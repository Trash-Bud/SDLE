from email import message
import uuid


class Message:
    def __init__(self, messageContent, subscribers=set(), id=None) -> None:
        if id:
            self.id = id
        else:
            self.id = uuid.uuid4().hex
        self.messageContent = messageContent
        self.subscribersToRead = subscribers
        self.active = True

    def get_message(self, subscriberID):
        if subscriberID in self.subscribersToRead:
            self.subscribersToRead.remove(subscriberID)
        if not self.subscribersToRead:
            self.active = False

    def sub_message(self, subscriberID):
        self.subscribersToRead.add(subscriberID)

    def hasSubscriberRead(self, subscriberID):
        return subscriberID in self.subscribersToRead

    def __str__(self) -> str:
        return f""" 
            MessageID: {self.id}
            MessageContent: {self.messageContent}
            SubscribersToRead: {self.subscribersToRead}
        """

    def to_json(self):
        return {"messageID": self.id, "messageContent": self.messageContent, "subscribersToRead": list(self.subscribersToRead)}

    def from_json(json_message):
        return Message(json_message["messageContent"], set(json_message["subscribersToRead"]), json_message["messageID"])


class Topic:
    def __init__(self, topicName) -> None:
        self.topicName = topicName
        self.subscribers = set()
        self.messages = []

    def subscribe(self, subscriberID):
        self.subscribers.add(subscriberID)
        for message in self.messages:
            message.sub_message(subscriberID)

    def put(self, message):
        self.messages.append(message)

    def unsubscribe(self, unsubsriberID):
        self.subscribers.remove(unsubsriberID)
        for message in self.messages:
            message.get_message(unsubsriberID)
        self.updateMessageList()

    def updateMessageList(self):
        self.messages = [
            message for message in self.messages if message.active]

    def get(self, subscriberID):
        for message in self.messages:
            if message.hasSubscriberRead(subscriberID):
                message.get_message(subscriberID)
                self.updateMessageList()
                return message

    def __str__(self):
        messagesStr = []
        for message in self.messages:
            messagesStr.append(message.__str__())
        return f'''
                TopicName: {self.topicName}
                Subscribers: {self.subscribers}
                Messages: {messagesStr}
            '''

    def to_json(self):
        return {"topicName": self.topicName, "subscribers": list(self.subscribers), "messages": [message.to_json() for message in self.messages]}

    def from_json(topic_json):
        new_topic = Topic(topic_json["topicName"])
        for subs in topic_json["subscribers"]:
            new_topic.subscribe(subs)
        for message in topic_json["messages"]:
            new_topic.put(Message.from_json(message))
        return new_topic
