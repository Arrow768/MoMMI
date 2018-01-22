import logging
from typing import TYPE_CHECKING, Any, Optional, cast, Type, Iterable, TypeVar
from discord import Channel, Role, Member
from MoMMI.types import SnowflakeID
from MoMMI.config import get_nested_dict_value, ConfigError
from MoMMI.role import MRoleType

logger = logging.getLogger(__name__)
T = TypeVar("T")

class MChannel(object):
    """
    Represents extra context for a channel.
    This is the type most commands will be interacting with.
    Handles everything from roles to sending messages.
    """

    if TYPE_CHECKING:
        from MoMMI.server import MServer

    def __init__(self, server: "MServer", channel: Channel, name: Optional[str]) -> None:
        from MoMMI.server import MServer
        self.id: SnowflakeID = SnowflakeID(channel.id)
        self.internal_name: Optional[str] = name
        self.server: MServer = server

    @property
    def name(self) -> str:
        return cast(str, self.get_channel().name)

    def get_channel(self) -> Channel:
        """
        Gets our discord.Channel.
        The channel instance is not permanently stored for reasons.
        """
        return self.server.master.client.get_channel(str(self.id))

    async def send(self, message: str = "", **kwargs: Any):
        """
        Send a message on this channel.
        """
        channel = self.get_channel()
        await self.server.master.client.send_message(channel, message, **kwargs)

    def module_config(self, key: str, default: Optional[T] = None) -> T:
        """
        Get global (module level) config data. That means it's from `modules.toml`
        """
        return self.server.master.config.get_module(key, default)

    def main_config(self, key: str, default: Optional[T] = None) -> T:
        return self.server.master.config.get_main(key, default)

    def server_config(self, key: str, default: Optional[T] = None) -> T:
        ret = cast(Optional[T], get_nested_dict_value(self.server.config, key))
        if ret is not None:
            return ret

        if default is None:
            raise ValueError("Unable to get config key and no default specified.")

        return default

    def isrole(self, member: Member, rolename: MRoleType) -> bool:
        if rolename == MRoleType.OWNER:
            owner_id = self.main_config("bot.owner")
            return int(member.id) == owner_id

        if rolename not in self.server.roles:
            return False

        snowflake = self.server.roles[rolename]

        for role in member.roles:
            if SnowflakeID(role.id) == snowflake:
                return True

        return False

    def iter_handlers(self, handlertype: Type[T]) -> Iterable[T]:
        for module in self.server.modules.values():
            yield from (x for x in module.handlers.values() if isinstance(x, handlertype))

    def get_storage(self, name: str) -> Any:
        return self.server.get_storage(name)

    def set_storage(self, name: str, value: Any) -> None:
        self.server.set_storage(name, value)

    async def save_storage(self, name: str) -> None:
        await self.server.save_storage(name)

    async def save_all_storages(self) -> None:
        await self.server.save_all_storages()

    def get_cache(self, name: str) -> Any:
        return self.server.get_cache(name)

    def set_cache(self, name: str, value: Any) -> None:
        self.server.set_cache(name, value)

    def get_global_cache(self, name: str) -> Any:
        return self.server.master.cache[name]

    def set_global_cache(self, name: str, value: Any) -> None:
        self.server.master.cache[name] = value

    def get_role_snowflake(self, snowflake: SnowflakeID) -> Role:
        for role in self.server.get_server().roles:
            if SnowflakeID(role.id) == snowflake:
                return role

        return ValueError(f"Unknown role {snowflake}")

    def get_role(self, name: MRoleType) -> Role:
        try:
            snowflake = self.server.roles[name]
        except KeyError:
            # Logging this on top of the raised exception because it's a config issue.
            logger.warning(f"Attempted to get unknown role '$YELLOW{name}$RESET' on server '$YELLOW{self.server.name}$RESET'.")
            raise

        server = self.server.get_server()
        for role in server.roles:
            if SnowflakeID(role.id) == snowflake:
                return role

        raise ConfigError(f"Unable to find role {snowflake}!")

    def get_member_named(self, name: str) -> Member:
        return self.server.get_server().get_member_named(name)

    def get_member(self, snowflake: SnowflakeID) -> Member:
        return self.server.get_server().get_member(str(snowflake))
