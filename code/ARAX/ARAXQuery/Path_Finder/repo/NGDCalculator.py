import math

NGD_normalizer = 3.5e+7 * 20
log_NGD_normalizer = math.log(NGD_normalizer)


def calculate_ngd(first_element_set, second_element_set):
    if first_element_set is None or second_element_set is None:
        return None

    log_length_of_first_element = math.log(len(first_element_set))
    log_length_of_second_element = math.log(len(second_element_set))
    joint_count = len(first_element_set.intersection(second_element_set))

    if log_length_of_first_element == 0 or log_length_of_second_element == 0:
        return None
    elif joint_count == 0:
        return None
    else:
        try:
            return (max([log_length_of_first_element, log_length_of_second_element]) - math.log(joint_count)) / \
                (log_NGD_normalizer - min([log_length_of_first_element, log_length_of_second_element]))
        except ValueError:
            return None
