from RTXFeedback import RTXFeedback
araxdb = RTXFeedback()
message_dict = araxdb.getMessage(18)
from ARAX_messenger import ARAXMessenger
message = ARAXMessenger().from_dict(message_dict)