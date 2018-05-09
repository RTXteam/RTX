
''' This module defines the class GenerateMetabolitesTSV. GenerateMetabolitesTSV class is designed
to generate the metabolites.tsv file.

The format of the metabolites.tsv looks like the following:

metabolite	KEGG:C00022	Pyruvate	generic

'''


__author__ = 'Deqing Qu'
__copyright__ = 'Oregon State University'
__credits__ = ['Deqing Qu', 'Stephen Ramsey']
__license__ = 'MIT'
__version__ = '0.1.0'
__maintainer__ = ''
__email__ = ''
__status__ = 'Prototype'


import requests
import sys


class GenerateMetabolitesTSV:

    FILE_NAME = 'metabolites.tsv'
    URL = 'http://rest.kegg.jp/list/compound'

    @staticmethod
    def __retrieve_entries_from_url():

        #   network request
        try:
            res = requests.get(GenerateMetabolitesTSV.URL)
        except requests.exceptions.Timeout:
            print(GenerateMetabolitesTSV.URL, file=sys.stderr)
            print("Timeout for URL: " + GenerateMetabolitesTSV.URL, file=sys.stderr)
            return False
        status_code = res.status_code
        if status_code != 200:
            print(GenerateMetabolitesTSV.URL, file=sys.stderr)
            print('Status code ' + str(status_code) + ' for url: ' + GenerateMetabolitesTSV.URL, file=sys.stderr)
            return False

        #   save content to file
        with open(GenerateMetabolitesTSV.FILE_NAME, 'wb') as fd:
            for chunk in res.iter_content(1024):
                fd.write(chunk)

        return True

    @staticmethod
    def __process_all_entries():
        content = ''
        try:
            rf = open(GenerateMetabolitesTSV.FILE_NAME, 'r+')
            for line in rf.readlines():
                line = GenerateMetabolitesTSV.__process_line_content(line)
                content += 'metabolite\t' + line + '\tgeneric\n'
            rf.close()
        except OSError as err:
            print("reading file, OS error: {0}".format(err))

        try:
            wf = open(GenerateMetabolitesTSV.FILE_NAME, 'w+')
            wf.write(content)
            wf.close()
        except OSError as err:
            print("writing file, OS error: {0}".format(err))

    @staticmethod
    def __process_line_content(line):
        line = line.replace('cpd', 'KEGG')
        semicolon_pos = line.find(';')
        if semicolon_pos == -1:
            line = line[:len(line)-1]
        else:
            line = line[:semicolon_pos]
        return line

    @staticmethod
    def generate_metabolites_tsv():
        if GenerateMetabolitesTSV.__retrieve_entries_from_url():
            GenerateMetabolitesTSV.__process_all_entries()


if __name__ == '__main__':
    GenerateMetabolitesTSV.generate_metabolites_tsv()