from dataclasses import dataclass


@dataclass
class MetaData:
    key: str
    type: str
    value: any
