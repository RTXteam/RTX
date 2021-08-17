import pprint

import six
import typing

from openapi_server import util

T = typing.TypeVar('T')


class Model(object):
    # openapiTypes: The key is attribute name and the
    # value is attribute type.
    openapi_types = {}

    # attributeMap: The key is attribute name and the
    # value is json key in definition.
    attribute_map = {}

    @classmethod
    def from_dict(cls: typing.Type[T], dikt) -> T:
        """Returns the dict as a model"""
        return util.deserialize_model(dikt, cls)

    def to_dict(self):
        """Returns the model properties as a dict

        :rtype: dict
        """
        result = {}

        for attr, _ in six.iteritems(self.openapi_types):
            value = getattr(self, attr)
            if isinstance(value, list):
                result[attr] = list(map(
                    lambda x: x.to_dict() if hasattr(x, "to_dict") else x,
                    value
                ))
            elif hasattr(value, "to_dict"):
                result[attr] = value.to_dict()
            elif isinstance(value, dict):

                #### This only can handle one level of lists or dicts between objects
                #result[attr] = dict(map(
                #    lambda item: (item[0], item[1].to_dict())
                #    if hasattr(item[1], "to_dict") else item,
                #    value.items()
                #))

                #### This is a little fancier in that it can handle two levels, a dict and then
                #### another dict or list between objects. Not the ultimate solution but
                #### perhaps adequate for now?
                result_dict = {}
                for dict_key, dict_value in value.items():
                    if isinstance(dict_value, list):
                        result_dict[dict_key] = list(map(
                            lambda x: x.to_dict() if hasattr(x, "to_dict") else x,
                            dict_value
                        ))
                    elif isinstance(dict_value, dict):
                        result_dict[dict_key] = dict(map(
                            lambda dict_value_item: (dict_value_item[0], dict_value_item[1].to_dict())
                            if hasattr(dict_value_item[1], "to_dict") else dict_value_item,
                            dict_value.items()
                        ))
                    elif hasattr(dict_value, "to_dict"):
                        result_dict[dict_key] = dict_value.to_dict()
                    else:
                        result_dict[dict_key] = dict_value
                result[attr] = result_dict

            else:
                if attr == '_not':
                    attr = 'not'
                result[attr] = value

        return result

    def to_str(self):
        """Returns the string representation of the model

        :rtype: str
        """
        return pprint.pformat(self.to_dict())

    def __repr__(self):
        """For `print` and `pprint`"""
        return self.to_str()

    def __eq__(self, other):
        """Returns true if both objects are equal"""
        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        """Returns true if both objects are not equal"""
        return not self == other
