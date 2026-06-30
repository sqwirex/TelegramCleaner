from telethon import TelegramClient, functions


class ReactionLookupMixin:
    async def _message_has_my_reaction(self, tg_client: TelegramClient, entity, message) -> bool:
        reactions = getattr(message, "reactions", None)
        if reactions is None:
            return False
        for result in getattr(reactions, "results", []) or []:
            if getattr(result, "chosen_order", None) is not None:
                return True
        try:
            me = await tg_client.get_me()
            data = await tg_client(functions.messages.GetMessageReactionsListRequest(peer=entity, id=message.id, limit=100))
            for reaction in getattr(data, "reactions", []) or []:
                peer = getattr(reaction, "peer_id", None)
                if getattr(peer, "user_id", None) == getattr(me, "id", None):
                    return True
        except Exception:
            return False
        return False