from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import BigInteger
from sqlalchemy import String
from sqlalchemy import Float
from sqlalchemy import Index

from backend.database.session import Base


class Transaction(Base):

    __tablename__ = "transactions"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    transaction_id = Column(
        String,
        unique=True,
        nullable=False,
        index=True
    )

    step = Column(
        Integer,
        nullable=False,
        index=True
    )

    type = Column(
        String,
        nullable=False,
        index=True
    )

    amount = Column(
        Float,
        nullable=False
    )

    name_orig = Column(
        String,
        nullable=False,
        index=True
    )

    old_balance_org = Column(
        Float,
        nullable=False
    )

    new_balance_orig = Column(
        Float,
        nullable=False
    )

    name_dest = Column(
        String,
        nullable=False,
        index=True
    )

    old_balance_dest = Column(
        Float,
        nullable=False
    )

    new_balance_dest = Column(
        Float,
        nullable=False
    )

    is_fraud = Column(
        Integer,
        nullable=False,
        default=0,
        index=True
    )

    is_flagged_fraud = Column(
        Integer,
        nullable=False,
        default=0
    )
