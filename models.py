from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(String, nullable=False)
    description = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    category = Column(String, default="Uncategorized")
    currency = Column(String(3), nullable=True)


class BankCustomer(Base):
    __tablename__ = "bank_customers"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    provider_customer_id = Column(String, nullable=False, unique=True, index=True)


class BankConnection(Base):
    __tablename__ = "bank_connections"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    provider_connection_id = Column(String, nullable=False, unique=True, index=True)
    provider_name = Column(String, nullable=False, default="Bank")
    status = Column(String, nullable=False, default="active")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class BankImportedTransaction(Base):
    __tablename__ = "bank_imported_transactions"
    __table_args__ = (UniqueConstraint("connection_id", "provider_transaction_id", name="uq_bank_tx_connection_external"),)

    id = Column(Integer, primary_key=True)
    connection_id = Column(Integer, ForeignKey("bank_connections.id"), nullable=False, index=True)
    provider_transaction_id = Column(String, nullable=False)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False, unique=True)

  

