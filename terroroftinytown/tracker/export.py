# encoding=utf-8

import os, lzma

from sqlalchemy import func
from sqlalchemy.orm.session import make_transient

from terroroftinytown.tracker.bootstrap import Bootstrap
from terroroftinytown.format import registry
from terroroftinytown.format.urlformat import quote
from terroroftinytown.tracker.model import new_session, Project, Result

class Exporter:
    projects_count = 0
    items_count = 0
    last_item = None

    output_dir = ''
    settings = {}

    lzma = True
    extension = 'txt.xz'

    # Length of directory name
    dir_length = 2
    # Number of characters from the right are not used in directory name
    # in other words, number of _
    max_right = 4
    # Number of characters from the left that are used in file name
    # in other words, number of characters that are not in directory name and not _
    file_length = 2

    # Example of settings:
    # dir_length = 2
    # max_right = 4
    # file_length = 2
    # output: projectname/00/01/000100____.txt, projectname/01/01__.txt

    def __init__(self, output_dir, format="beacon", settings={}):
        self.setup_format(format)
        self.output_dir = output_dir
        self.settings = settings

    def setup_format(self, format):
        self.format = registry[format]

    def dump(self):
        if not os.path.isdir(self.output_dir):
            os.makedirs(self.output_dir)

        with new_session() as session:
            for project in session.query(Project):
                self.dump_project(project)

    def dump_project(self, project):
        print('Looking in project %s' % (project.name))
        with new_session() as session:
            query = session.query(Result) \
                .filter_by(project=project) \
                .order_by(func.length(Result.shortcode), Result.shortcode)

            if self.settings['after']:
                query = query.filter(Result.datetime > self.settings['after'])

            count = query.count()
            if count == 0:
                return

            self.projects_count += 1

            # XXX: Use regex \{shortcode\}$ instead?
            site = project.url_template.replace('{shortcode}', '')

            fp = None
            writer = None
            last_filename = ''
            i = 0

            for item in query:
                self.items_count += 1
                i += 1

                if i % 1000 == 0:
                    print('%d/%d' % (i, count))

                # we can do this as the query is sorted
                # so that item that would end up together
                # would returned together
                filename = self.get_filename(project, item)
                if filename != last_filename:
                    if fp and writer:
                        writer.write_footer()
                        fp.close()

                    # assert not os.path.isfile(filename), 'Target file %s already exists' % (filename)

                    if self.lzma:
                        fp = lzma.open(filename, 'wb')
                    else:
                        fp = open(filename, 'wb')
                    writer = self.format(fp)
                    writer.write_header(site)

                    last_filename = filename

                writer.write_shortcode(item.shortcode, item.url, item.encoding)
                self.last_item = item

            if fp and writer:
                writer.write_footer()
                fp.close()

            make_transient(self.last_item)


    def get_filename(self, project, item):
        path = os.path.join(self.output_dir, project.name)

        #0001asdf
        # dir_length max_right file_length
        shortcode = item.shortcode

        # create directories until we left only max_right or less characters
        length = 0
        while len(shortcode) > self.max_right + self.file_length:
            dirname = shortcode[:2]
            length += len(dirname)
            path = os.path.join(path, quote(dirname.encode(item.encoding)))
            shortcode = shortcode[2:]

        # name the file
        code_length = len(item.shortcode)
        length_left = code_length - length
        underscores = min(length_left, self.max_right)
        path = os.path.join(path, '%s%s.%s' % (
            quote(item.shortcode[:code_length - underscores].encode(item.encoding)),
            '_' * underscores,
            self.extension
        ))

        dirname = os.path.dirname(path)
        if not os.path.isdir(dirname):
            os.makedirs(dirname)

        return path

class ExporterBootstrap(Bootstrap):
    def __init__(self):
        super().__init__()

        self.exporter = Exporter(self.args.output_dir, self.args.format, vars(self.args))
        self.exporter.dump()
        self.write_stats()

    def setup_args(self):
        super().setup_args()
        self.arg_parser.add_argument('--format', default='beacon',
            choices=registry.keys(), help='Output file format')
        self.arg_parser.add_argument('--after', help='Only export items submitted after specified time. (ISO8601 format YYYY-MM-DDTHH:MM:SS.mmmmmm)')
        self.arg_parser.add_argument('output_dir', help='Output directory (will be created)')

    def write_stats(self):
        print('Written %d items in %d projects' % (self.exporter.projects_count, self.exporter.items_count))
        if self.exporter.last_item:
            print('Last item timestamp (use --after to dump after this item):')
            print(self.exporter.last_item.datetime.isoformat())
    

if __name__ == '__main__':
    ExporterBootstrap()