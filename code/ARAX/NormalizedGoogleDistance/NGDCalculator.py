import math


def calculate_ngd(log_of_length_of_first_pmid, length_of_second_pmid, length_of_intersection, log_of_NGD_normalizer):
    if log_of_length_of_first_pmid == 0 or length_of_second_pmid == 0 or length_of_intersection == 0:
        return None

    log_of_length_of_second_element = math.log(length_of_second_pmid)
    try:
        return (max([log_of_length_of_first_pmid, log_of_length_of_second_element]) - math.log(
            length_of_intersection)) / \
            (log_of_NGD_normalizer - min([log_of_length_of_first_pmid, log_of_length_of_second_element]))
    except ValueError:
        return None
