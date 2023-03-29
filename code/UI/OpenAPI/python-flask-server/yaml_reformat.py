#!/usr/bin/python3
import yaml



############################################ Main ############################################################
def main():

    input_filename = 'RTX_OA3_TRAPI1.3_ARAX.yaml'
    output_filename = 'RTX_OA3_TRAPI1.3_ARAX_reformat.yaml'

    with open(input_filename) as infile:
        content = yaml.safe_load(infile)

    with open(output_filename, 'w') as outfile:
        yaml.dump(content, outfile)

    return


if __name__ == "__main__": main()
