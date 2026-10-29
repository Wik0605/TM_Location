from uuid import UUID

import uuid_utils


def new_uuid7() -> UUID:
    return UUID(str(uuid_utils.uuid7()))
