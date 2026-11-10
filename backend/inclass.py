"""
Hostel Borrowing Club System - Green View Hostel
Author: Nyabwana Simon Peter

OOP concepts demonstrated (search for the tag in brackets):
  [ABSTRACTION]      Describable, User, Item are abstract (ABC + @abstractmethod)
  [INHERITANCE]      User -> HostelAdministrator / ClubMember
                     Item -> ElectronicItem / ApplianceItem / BookItem / HouseholdItem
  [MULTIPLE INHERIT] User and Item inherit from Describable AND ReportableMixin
  [ENCAPSULATION]    private (name-mangled) attributes, properties, validated setters
  [POLYMORPHISM]     overridden describe(), menu(), max_borrow_days, penalty_per_day
  [DUCK TYPING]      notifiers share no base class; any object with send() works
  [CONSTRUCTORS]     __init__ with super(), default args, @classmethod from_csv,
                     ItemFactory (factory pattern)
  [CLASS/STATIC]     class variables, @classmethod, @staticmethod
  [OPERATORS]        __eq__, __lt__, __hash__, __len__, __iter__, __contains__, __repr__
  [COMPOSITION]      BorrowingClub is made of members, admins, requests, notifiers
  [EXCEPTIONS]       custom exception hierarchy
  [OTHER]            Enums, dataclass, generator, template-method pattern, type hints
"""

from __future__ import annotations

import hashlib
import itertools
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum
from functools import total_ordering
from typing import Iterator, Optional


# ==========================================================================
# Enumerations
# ==========================================================================
class UserRole(Enum):
    ADMINISTRATOR = "Administrator"
    MEMBER = "Club Member"


class ItemStatus(Enum):
    AVAILABLE = "Available"
    BORROWED = "Borrowed"


class RequestStatus(Enum):
    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    BORROWED = "Borrowed"
    OVERDUE = "Overdue"
    RETURNED = "Returned"


# ==========================================================================
# [EXCEPTIONS] Custom exception hierarchy
# ==========================================================================
class ClubError(Exception):
    """Base class for every error raised by the club."""


class ValidationError(ClubError):
    """Bad input (empty name, invalid phone, unknown category ...)."""


class AuthenticationError(ClubError):
    """Wrong username or password."""


class PermissionDeniedError(ClubError):
    """User tried to do something that belongs to someone else."""


class ItemUnavailableError(ClubError):
    """Item is not free to be borrowed."""


class InvalidStateError(ClubError):
    """Action not allowed in the request's current state."""


# ==========================================================================
# [ABSTRACTION] Abstract base class (acts as an interface)
# ==========================================================================
class Describable(ABC):
    @abstractmethod
    def describe(self) -> str:
        """Return a one-line human readable description."""


# ==========================================================================
# [MULTIPLE INHERITANCE] Mixin: reusable behaviour, not meant to stand alone
# ==========================================================================
class ReportableMixin:
    """Gives any class to_dict() / to_json(). Subclass supplies _report_data()."""

    def _report_data(self) -> dict:
        raise NotImplementedError("Subclass must provide _report_data()")

    def to_dict(self) -> dict:
        out = {}
        for key, value in self._report_data().items():
            if isinstance(value, Enum):
                value = value.value
            elif isinstance(value, date):
                value = value.isoformat()
            out[key] = value
        return out

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


# ==========================================================================
# Users  [ABSTRACTION] [INHERITANCE] [ENCAPSULATION]
# ==========================================================================
class User(Describable, ReportableMixin):
    """Abstract base class for everyone who can log in."""

    _counter = itertools.count(1)          # [CLASS VARIABLE] shared by all users
    MIN_PASSWORD_LENGTH = 4

    # [CONSTRUCTOR]
    def __init__(self, name: str, username: str, password: str):
        # Double underscore => name mangling => truly private to this class
        self.__user_id = next(User._counter)
        self.__name = ""
        self.name = name                                   # uses validated setter
        self.__username = self._clean_username(username)
        self.__password_hash = self._hash(self._check_password_rules(password))

    # ---- [ENCAPSULATION] read-only and validated properties ----
    @property
    def user_id(self) -> int:
        return self.__user_id

    @property
    def username(self) -> str:
        return self.__username

    @property
    def name(self) -> str:
        return self.__name

    @name.setter
    def name(self, value: str) -> None:
        if not value or not value.strip():
            raise ValidationError("Name cannot be empty.")
        self.__name = value.strip().title()

    # ---- [ABSTRACTION] subclasses MUST implement these ----
    @property
    @abstractmethod
    def role(self) -> UserRole: ...

    @abstractmethod
    def menu(self) -> list[str]:
        """Actions this kind of user may perform."""

    # ---- security ----
    def check_password(self, password: str) -> bool:
        return self.__password_hash == self._hash(password)

    def change_password(self, old: str, new: str) -> None:
        if not self.check_password(old):
            raise AuthenticationError("Old password is incorrect.")
        self.__password_hash = self._hash(self._check_password_rules(new))

    def update_profile(self, name: str, username: str) -> None:
        self.name = name
        clean_username = self._clean_username(username)
        self.__username = clean_username

    def reset_password(self, new_password: str) -> None:
        self.__password_hash = self._hash(self._check_password_rules(new_password))

    # ---- [STATIC METHODS] helpers that need no object state ----
    @staticmethod
    def _hash(password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()

    @staticmethod
    def _clean_username(username: str) -> str:
        username = (username or "").strip().lower()
        if not username or " " in username:
            raise ValidationError("Username must be one word and cannot be empty.")
        return username

    @classmethod
    def _check_password_rules(cls, password: str) -> str:
        if len(password or "") < cls.MIN_PASSWORD_LENGTH:
            raise ValidationError(f"Password must have at least {cls.MIN_PASSWORD_LENGTH} characters.")
        return password

    # ---- concrete implementation of the abstract Describable method ----
    def describe(self) -> str:
        return f"{self.role.value} #{self.user_id}: {self.name}"

    def _report_data(self) -> dict:
        return {"id": self.user_id, "name": self.name, "username": self.username,
                "role": self.role}

    # ---- [OPERATORS] ----
    def __eq__(self, other: object) -> bool:
        return isinstance(other, User) and self.user_id == other.user_id

    def __hash__(self) -> int:
        return hash(self.user_id)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(id={self.user_id}, name={self.name!r})"

    def __str__(self) -> str:
        return self.describe()


class HostelAdministrator(User):
    """Registers members and manages the club."""

    @property
    def role(self) -> UserRole:                      # [POLYMORPHISM] overriding
        return UserRole.ADMINISTRATOR

    def menu(self) -> list[str]:                     # [POLYMORPHISM] overriding
        return ["Register member", "View all members", "View overdue items",
                "View full borrowing history"]

    def register_member(self, club: "BorrowingClub", name: str, username: str,
                        password: str, room_number: str, phone: str) -> "ClubMember":
        return club.register_member(name, username, password, room_number, phone)


class ClubMember(User):
    """A student who lives in the hostel. Owns items and borrows items."""

    MAX_ITEMS = 10                                   # [CLASS VARIABLE]

    # [CONSTRUCTOR] calls the parent constructor with super()
    def __init__(self, name: str, username: str, password: str,
                 room_number: str, phone: str):
        super().__init__(name, username, password)
        self.__room_number = ""
        self.__phone = ""
        self.room_number = room_number               # validated setters
        self.phone = phone
        self.__items: list[Item] = []                # [COMPOSITION] member owns items

    # [CONSTRUCTOR] alternative constructor
    @classmethod
    def from_csv(cls, line: str, default_password: str = "member123") -> "ClubMember":
        """Build a member from 'Name,username,room,phone'."""
        try:
            name, username, room, phone = [p.strip() for p in line.split(",")]
        except ValueError:
            raise ValidationError("CSV line must be: name,username,room,phone") from None
        return cls(name, username, default_password, room, phone)

    @staticmethod
    def is_valid_phone(phone: str) -> bool:
        return phone.isdigit() and len(phone) == 10

    @property
    def role(self) -> UserRole:
        return UserRole.MEMBER

    def menu(self) -> list[str]:
        return ["Add item", "View available items", "Request to borrow",
                "Approve / reject requests", "Return item", "View my history"]

    # ---- validated properties ----
    @property
    def room_number(self) -> str:
        return self.__room_number

    @room_number.setter
    def room_number(self, value: str) -> None:
        if not value or not value.strip():
            raise ValidationError("Room number cannot be empty.")
        self.__room_number = value.strip().upper()

    @property
    def phone(self) -> str:
        return self.__phone

    @phone.setter
    def phone(self, value: str) -> None:
        if not self.is_valid_phone(value):
            raise ValidationError("Phone must be exactly 10 digits.")
        self.__phone = value

    @property
    def items(self) -> tuple["Item", ...]:
        return tuple(self.__items)                   # immutable copy protects the list

    def add_item(self, category: str, name: str, description: str = "", **extras) -> "Item":
        if len(self.__items) >= self.MAX_ITEMS:
            raise ValidationError(f"A member can list at most {self.MAX_ITEMS} items.")
        item = ItemFactory.create(category, name, description, self, **extras)
        self.__items.append(item)
        return item

    def describe(self) -> str:                       # [POLYMORPHISM] extends parent
        return f"{super().describe()} (Room {self.room_number})"

    def _report_data(self) -> dict:
        data = super()._report_data()
        data.update(room=self.room_number, phone=self.phone, items_listed=len(self.__items))
        return data


# ==========================================================================
# Items  [ABSTRACTION] [INHERITANCE] [POLYMORPHISM]
# ==========================================================================
@total_ordering                                      # fills in <=, >, >= from __lt__
class Item(Describable, ReportableMixin):
    """Abstract base class for anything a member can lend."""

    _counter = itertools.count(1)
    CATEGORY = "General"                             # overridden in subclasses

    def __init__(self, name: str, description: str, owner: ClubMember):
        if not name or not name.strip():
            raise ValidationError("Item name cannot be empty.")
        if getattr(owner, "role", None) is not UserRole.MEMBER:   # duck-typed check
            raise ValidationError("An item must be owned by a club member.")
        self.__item_id = next(Item._counter)
        self.__name = name.strip().title()
        self.__description = description
        self.__owner = owner
        self.__status = ItemStatus.AVAILABLE

    # ---- read-only properties ----
    @property
    def item_id(self) -> int:
        return self.__item_id

    @property
    def name(self) -> str:
        return self.__name

    @property
    def description(self) -> str:
        return self.__description

    @property
    def owner(self) -> ClubMember:
        return self.__owner

    @property
    def status(self) -> ItemStatus:
        return self.__status

    # ---- [ABSTRACTION] every category must define its own rules ----
    @property
    @abstractmethod
    def max_borrow_days(self) -> int: ...

    @property
    @abstractmethod
    def penalty_per_day(self) -> int:
        """Late fee per day in UGX."""

    # ---- [TEMPLATE METHOD] concrete method that uses the abstract rules ----
    def calculate_penalty(self, days_late: int) -> int:
        return max(days_late, 0) * self.penalty_per_day

    # ---- state changes controlled by the object itself ----
    def is_available(self) -> bool:
        return self.__status is ItemStatus.AVAILABLE

    def mark_borrowed(self) -> None:
        if not self.is_available():
            raise ItemUnavailableError(f"'{self.name}' is already borrowed.")
        self.__status = ItemStatus.BORROWED

    def mark_available(self) -> None:
        self.__status = ItemStatus.AVAILABLE

    def describe(self) -> str:
        return (f"#{self.item_id} {self.name} [{self.CATEGORY}] - owner: "
                f"{self.owner.name} - {self.status.value}")

    def _report_data(self) -> dict:
        return {"id": self.item_id, "name": self.name, "category": self.CATEGORY,
                "owner": self.owner.name, "status": self.status,
                "max_days": self.max_borrow_days}

    # ---- [OPERATORS] ----
    def __eq__(self, other: object) -> bool:
        return isinstance(other, Item) and self.item_id == other.item_id

    def __lt__(self, other: "Item") -> bool:         # sorting by name
        return self.name.lower() < other.name.lower()

    def __hash__(self) -> int:
        return hash(self.item_id)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(id={self.item_id}, name={self.name!r})"

    def __str__(self) -> str:
        return self.describe()


class ElectronicItem(Item):
    CATEGORY = "Electronic"

    def __init__(self, name: str, description: str, owner: ClubMember, brand: str = "Generic"):
        super().__init__(name, description, owner)
        self.__brand = brand

    @property
    def max_borrow_days(self) -> int:
        return 4

    @property
    def penalty_per_day(self) -> int:
        return 2000

    def describe(self) -> str:
        return f"{super().describe()} | brand: {self.__brand}"

    def _report_data(self) -> dict:
        return {**super()._report_data(), "brand": self.__brand}


class ApplianceItem(Item):
    CATEGORY = "Appliance"

    def __init__(self, name: str, description: str, owner: ClubMember, power_watts: int = 0):
        super().__init__(name, description, owner)
        self.__power_watts = power_watts

    @property
    def max_borrow_days(self) -> int:
        return 4

    @property
    def penalty_per_day(self) -> int:
        return 3000

    def describe(self) -> str:
        return f"{super().describe()} | {self.__power_watts}W"


class BookItem(Item):
    CATEGORY = "Book"

    def __init__(self, name: str, description: str, owner: ClubMember, author: str = "Unknown"):
        super().__init__(name, description, owner)
        self.__author = author

    @property
    def max_borrow_days(self) -> int:
        return 4

    @property
    def penalty_per_day(self) -> int:
        return 500

    def describe(self) -> str:
        return f"{super().describe()} | author: {self.__author}"


class HouseholdItem(Item):
    CATEGORY = "Household"

    @property
    def max_borrow_days(self) -> int:
        return 4

    @property
    def penalty_per_day(self) -> int:
        return 1000


# ==========================================================================
# [CONSTRUCTORS] Factory: chooses the right subclass from a category name
# ==========================================================================
class ItemFactory:
    _registry: dict[str, type[Item]] = {}

    @classmethod
    def register(cls, item_class: type[Item]) -> None:
        cls._registry[item_class.CATEGORY.lower()] = item_class

    @classmethod
    def categories(cls) -> list[str]:
        return sorted(c.title() for c in cls._registry)

    @classmethod
    def create(cls, category: str, name: str, description: str,
               owner: ClubMember, **extras) -> Item:
        item_class = cls._registry.get(category.strip().lower())
        if item_class is None:
            raise ValidationError(f"Unknown category '{category}'. "
                                  f"Choose from: {', '.join(cls.categories())}")
        return item_class(name, description, owner, **extras)


for _cls in (ElectronicItem, ApplianceItem, BookItem, HouseholdItem):
    ItemFactory.register(_cls)


# ==========================================================================
# Borrow request (owns its life-cycle rules)
# ==========================================================================
class BorrowRequest(Describable, ReportableMixin):
    """
    PENDING -> APPROVED -> BORROWED -> RETURNED
    PENDING -> REJECTED
    BORROWED -> OVERDUE -> RETURNED
    """

    _counter = itertools.count(1)

    def __init__(self, item: Item, borrower: ClubMember, request_date: Optional[date] = None):
        self.__request_id = next(BorrowRequest._counter)
        self.__item = item
        self.__borrower = borrower
        self.__request_date = request_date or date.today()
        self.__status = RequestStatus.PENDING
        self.__agreed_days: Optional[int] = None
        self.__borrow_date: Optional[date] = None
        self.__due_date: Optional[date] = None
        self.__return_date: Optional[date] = None

    @property
    def request_id(self) -> int:
        return self.__request_id

    @property
    def item(self) -> Item:
        return self.__item

    @property
    def borrower(self) -> ClubMember:
        return self.__borrower

    @property
    def status(self) -> RequestStatus:
        return self.__status

    @property
    def borrow_date(self) -> Optional[date]:
        return self.__borrow_date

    @property
    def due_date(self) -> Optional[date]:
        return self.__due_date

    @property
    def return_date(self) -> Optional[date]:
        return self.__return_date

    # ---- guards ----
    def _require(self, *allowed: RequestStatus) -> None:
        if self.__status not in allowed:
            wanted = " / ".join(s.value for s in allowed)
            raise InvalidStateError(
                f"Request #{self.request_id} is {self.__status.value}; expected {wanted}.")

    def _require_owner(self, user: ClubMember) -> None:
        if user != self.__item.owner:
            raise PermissionDeniedError("Only the owner of the item can do this.")

    # ---- life-cycle ----
    def approve(self, owner: ClubMember, agreed_days: int) -> None:
        self._require(RequestStatus.PENDING)
        self._require_owner(owner)
        limit = self.__item.max_borrow_days
        if agreed_days != limit:
            raise ValidationError(
                f"{self.__item.CATEGORY} items must be borrowed for exactly {limit} days.")
        self.__agreed_days = agreed_days
        self.__status = RequestStatus.APPROVED

    def reject(self, owner: ClubMember) -> None:
        self._require(RequestStatus.PENDING)
        self._require_owner(owner)
        self.__status = RequestStatus.REJECTED

    def start_borrowing(self, borrower: ClubMember, today: Optional[date] = None) -> None:
        self._require(RequestStatus.APPROVED)
        if borrower != self.__borrower:
            raise PermissionDeniedError("Only the requesting member can collect this item.")
        self.__item.mark_borrowed()
        self.__borrow_date = today or date.today()
        self.__due_date = self.__borrow_date + timedelta(days=self.__agreed_days)
        self.__status = RequestStatus.BORROWED

    def confirm_return(self, owner: ClubMember, today: Optional[date] = None) -> None:
        self._require(RequestStatus.BORROWED, RequestStatus.OVERDUE)
        self._require_owner(owner)
        self.__return_date = today or date.today()
        self.__item.mark_available()
        self.__status = RequestStatus.RETURNED

    def update_overdue(self, today: Optional[date] = None) -> bool:
        today = today or date.today()
        if self.__status is RequestStatus.BORROWED and today > self.__due_date:
            self.__status = RequestStatus.OVERDUE
        return self.__status is RequestStatus.OVERDUE

    def days_overdue(self, today: Optional[date] = None) -> int:
        today = today or date.today()
        if self.__status in (RequestStatus.BORROWED, RequestStatus.OVERDUE) and today > self.__due_date:
            return (today - self.__due_date).days
        return 0

    def penalty(self, today: Optional[date] = None) -> int:
        """[POLYMORPHISM] the amount depends on the item's own subclass rules."""
        return self.__item.calculate_penalty(self.days_overdue(today))

    def describe(self) -> str:
        return (f"Request #{self.request_id}: {self.borrower.name} -> '{self.item.name}' "
                f"[{self.status.value}] borrowed={self.borrow_date or '-'} "
                f"due={self.due_date or '-'} returned={self.return_date or '-'}")

    def _report_data(self) -> dict:
        return {"id": self.request_id, "item": self.item.name, "borrower": self.borrower.name,
                "status": self.status, "borrow_date": self.borrow_date,
                "due_date": self.due_date, "return_date": self.return_date}

    def __str__(self) -> str:
        return self.describe()

    def __repr__(self) -> str:
        return f"BorrowRequest(id={self.request_id}, status={self.status.name})"


# ==========================================================================
# [DUCK TYPING] Notifiers: NO common base class. If it has send(), it works.
# ==========================================================================
@dataclass(frozen=True)
class Notification:
    recipient: str
    message: str
    sent_on: date


class ConsoleNotifier:
    def send(self, recipient: str, message: str) -> None:
        print(f"      [console] to {recipient}: {message}")


class LogNotifier:
    def __init__(self) -> None:
        self.__history: list[Notification] = []

    def send(self, recipient: str, message: str) -> None:
        self.__history.append(Notification(recipient, message, date.today()))

    @property
    def history(self) -> tuple[Notification, ...]:
        return tuple(self.__history)

    def __len__(self) -> int:
        return len(self.__history)


# ==========================================================================
# The system  [COMPOSITION / AGGREGATION]
# ==========================================================================
class BorrowingClub:
    """Holds every record and enforces the club's rules."""

    def __init__(self, hostel_name: str, notifiers: Optional[list] = None):
        self.__hostel_name = hostel_name
        self.__admins: list[HostelAdministrator] = []
        self.__members: list[ClubMember] = []
        self.__requests: list[BorrowRequest] = []
        self.__notifiers: list = []
        self.__current_user: Optional[User] = None
        for notifier in notifiers or []:
            self.add_notifier(notifier)

    @property
    def hostel_name(self) -> str:
        return self.__hostel_name

    @property
    def current_user(self) -> Optional[User]:
        return self.__current_user

    # ---------- duck-typed notifier registration ----------
    def add_notifier(self, notifier) -> None:
        if not callable(getattr(notifier, "send", None)):
            raise TypeError(f"{type(notifier).__name__} has no send() method")
        self.__notifiers.append(notifier)

    def _notify(self, user: User, message: str) -> None:
        for notifier in self.__notifiers:
            notifier.send(user.name, message)

    # ---------- 1. Register ----------
    def _ensure_unique_username(self, username: str) -> None:
        clean = User._clean_username(username)
        if any(u.username == clean for u in (*self.__admins, *self.__members)):
            raise ValidationError(f"Username '{clean}' is already taken.")

    def add_administrator(self, name: str, username: str, password: str) -> HostelAdministrator:
        self._ensure_unique_username(username)
        admin = HostelAdministrator(name, username, password)
        self.__admins.append(admin)
        return admin

    def register_member(self, name: str, username: str, password: str,
                        room_number: str, phone: str) -> ClubMember:
        return self.enroll(ClubMember(name, username, password, room_number, phone))

    def enroll(self, member: ClubMember) -> ClubMember:
        """Enrol an already-built member (e.g. made with ClubMember.from_csv)."""
        self._ensure_unique_username(member.username)
        self.__members.append(member)
        self._notify(member, f"Welcome to the {self.hostel_name} Borrowing Club!")
        return member

    # ---------- 2. Login ----------
    def login(self, username: str, password: str) -> User:
        for user in (*self.__admins, *self.__members):
            if user.username == username.strip().lower() and user.check_password(password):
                self.__current_user = user
                return user
        raise AuthenticationError("Invalid username or password.")

    def logout(self) -> None:
        self.__current_user = None

    # ---------- 3 & 4. Items ----------
    def add_item(self, owner: ClubMember, category: str, name: str,
                 description: str = "", **extras) -> Item:
        self._require_member(owner)
        return owner.add_item(category, name, description, **extras)

    def all_items(self) -> list[Item]:
        return [item for m in self.__members for item in m.items]

    def available_items(self) -> list[Item]:
        return [i for i in self.all_items() if i.is_available()]

    # ---------- 5. Request ----------
    def request_item(self, borrower: ClubMember, item: Item,
                     today: Optional[date] = None) -> BorrowRequest:
        self._require_member(borrower)
        if item.owner == borrower:
            raise PermissionDeniedError("You cannot borrow your own item.")
        if not item.is_available():
            raise ItemUnavailableError(f"'{item.name}' is not available.")
        if any(r.item == item and r.borrower == borrower and
               r.status in (RequestStatus.PENDING, RequestStatus.APPROVED)
               for r in self.__requests):
            raise InvalidStateError("You already have an open request for this item.")
        request = BorrowRequest(item, borrower, today)
        self.__requests.append(request)
        self._notify(item.owner, f"{borrower.name} wants to borrow your {item.name}.")
        return request

    # ---------- 6. Approve / reject ----------
    def pending_requests_for(self, owner: ClubMember) -> list[BorrowRequest]:
        return [r for r in self.__requests
                if r.item.owner == owner and r.status is RequestStatus.PENDING]

    def approve_request(self, owner: ClubMember, request: BorrowRequest, agreed_days: int) -> None:
        request.approve(owner, agreed_days)
        self._notify(request.borrower,
                     f"Your request for {request.item.name} was approved ({agreed_days} days).")

    def reject_request(self, owner: ClubMember, request: BorrowRequest) -> None:
        request.reject(owner)
        self._notify(request.borrower, f"Your request for {request.item.name} was rejected.")

    # ---------- 7. Borrow ----------
    def borrow_item(self, borrower: ClubMember, request: BorrowRequest,
                    today: Optional[date] = None) -> None:
        request.start_borrowing(borrower, today)

    # ---------- 8. Return ----------
    def return_item(self, owner: ClubMember, request: BorrowRequest,
                    today: Optional[date] = None) -> None:
        request.confirm_return(owner, today)
        self._notify(request.borrower, f"{request.item.name} confirmed returned. Thank you!")

    # ---------- 9. Overdue ----------
    def check_overdue(self, today: Optional[date] = None) -> list[BorrowRequest]:
        overdue = []
        for request in self.__requests:
            was_borrowed = request.status is RequestStatus.BORROWED
            if request.update_overdue(today):
                overdue.append(request)
                if was_borrowed:
                    self._notify(request.borrower,
                                 f"{request.item.name} is OVERDUE. Please return it.")
        return overdue

    def iter_overdue(self, today: Optional[date] = None) -> Iterator[BorrowRequest]:
        """[GENERATOR] yields overdue requests one at a time."""
        for request in self.__requests:
            if request.update_overdue(today):
                yield request

    # ---------- 10. History ----------
    def history_for(self, member: ClubMember) -> list[BorrowRequest]:
        return [r for r in self.__requests
                if r.borrower == member or r.item.owner == member]

    def full_history(self) -> list[BorrowRequest]:
        return list(self.__requests)

    def currently_borrowed(self) -> list[BorrowRequest]:
        return [r for r in self.__requests
                if r.status in (RequestStatus.BORROWED, RequestStatus.OVERDUE)]

    # ---------- helpers ----------
    def _require_member(self, member: ClubMember) -> None:
        if member not in self.__members:
            raise PermissionDeniedError("Only registered club members can do this.")

    # ---------- [OPERATORS] ----------
    def __len__(self) -> int:                        # len(club) -> number of members
        return len(self.__members)

    def __iter__(self) -> Iterator[BorrowRequest]:   # for r in club -> every request
        return iter(self.__requests)

    def __contains__(self, user: object) -> bool:    # member in club
        return user in self.__members or user in self.__admins

    def __repr__(self) -> str:
        return (f"BorrowingClub({self.hostel_name!r}, members={len(self.__members)}, "
                f"requests={len(self.__requests)})")


# ==========================================================================
# [DUCK TYPING] works with ANY object that has to_dict(): no isinstance check
# ==========================================================================
def print_report(title: str, records) -> None:
    print(f"\n--- {title} ---")
    for record in records:
        print("  ", record.to_dict())


class AdHocRecord:                                   # unrelated class, still works
    def to_dict(self) -> dict:
        return {"note": "I am not an Item or User, but I quack like one."}


# ==========================================================================
# Demonstration
# ==========================================================================
def heading(text: str) -> None:
    print(f"\n{'=' * 70}\n{text}\n{'=' * 70}")


def try_it(label: str, action) -> None:
    """Run an action that is expected to fail and show the error."""
    try:
        action()
    except (ClubError, TypeError, AttributeError) as error:
        print(f"  {label}: {type(error).__name__}: {error}")


def main() -> None:
    log = LogNotifier()
    club = BorrowingClub("Green View Hostel", notifiers=[ConsoleNotifier(), log])

    heading("1. CONSTRUCTORS: __init__, from_csv (classmethod), factory")
    admin = club.add_administrator("hostel warden", "admin", "admin123")
    brian = admin.register_member(club, "brian okello", "brian", "pass1", "a12", "0700000001")
    grace = club.enroll(ClubMember.from_csv("Grace Namukasa, grace, B05, 0700000002"))
    simon = club.register_member("Nyabwana Simon Peter", "simon", "pass3", "C07", "0700000003")
    print("  ", repr(club))

    heading("2. INHERITANCE + POLYMORPHISM: same call, different behaviour")
    for user in (admin, brian):
        print(f"  {user.describe()}\n     menu -> {user.menu()}")

    calculator = club.add_item(brian, "electronic", "scientific calculator", "Casio fx-991", brand="Casio")
    iron = club.add_item(brian, "appliance", "iron box", power_watts=1200)
    bucket = club.add_item(grace, "household", "bucket")
    textbook = club.add_item(grace, "book", "database systems", author="Elmasri")
    charger = club.add_item(grace, "electronic", "phone charger", brand="Samsung")
    print()
    for item in club.all_items():                    # one loop, 4 different classes
        print(f"  {item.describe()}\n     max {item.max_borrow_days} days, "
              f"penalty {item.penalty_per_day} UGX/day")

    heading("3. ENCAPSULATION: private data, validated setters, read-only properties")
    try_it("set read-only status", lambda: setattr(calculator, "status", ItemStatus.BORROWED))
    try_it("bad phone number", lambda: setattr(brian, "phone", "123"))
    try_it("short password", lambda: club.register_member("X Y", "xy", "1", "A1", "0700000009"))
    print("  direct access to __password_hash works? ->", hasattr(brian, "__password_hash"))
    brian.room_number = " a14 "
    print("  setter cleaned the room number ->", brian.room_number)

    heading("4. ABSTRACTION: abstract classes cannot be instantiated")
    try_it("User(...)", lambda: User("A B", "ab", "pass"))
    try_it("Item(...)", lambda: Item("Thing", "", brian))
    try_it("unknown category", lambda: brian.add_item("furniture", "chair"))

    heading("5. THE BORROWING FLOW (activities 5-9)")
    start = date(2026, 11, 1)
    r1 = club.request_item(simon, calculator, start)
    r2 = club.request_item(simon, charger, start)
    r3 = club.request_item(simon, iron, start)
    print("  Brian's pending requests:", [r.request_id for r in club.pending_requests_for(brian)])

    try_it("owner rule", lambda: club.approve_request(grace, r1, 2))
    try_it("period too long for an appliance", lambda: club.approve_request(brian, r3, 5))
    club.approve_request(brian, r1, 3)
    club.reject_request(grace, r2)
    club.reject_request(brian, r3)
    club.borrow_item(simon, r1, start)
    try_it("borrow own item", lambda: club.request_item(brian, calculator))
    try_it("item already borrowed", lambda: club.request_item(grace, calculator))

    today = start + timedelta(days=5)
    for late in club.iter_overdue(today):            # generator
        print(f"  {late.describe()}\n     late {late.days_overdue(today)} days -> "
              f"penalty {late.penalty(today)} UGX")
    club.check_overdue(today)
    club.return_item(brian, r1, today)

    heading("6. OPERATOR OVERLOADING (__eq__, __lt__, __len__, __iter__, __contains__)")
    print("  sorted items :", [i.name for i in sorted(club.all_items())])
    print("  calculator == calculator :", calculator == calculator)
    print("  calculator == iron box   :", calculator == iron)
    print("  len(club)    :", len(club), "members")
    print("  simon in club:", simon in club)
    print("  requests via for-loop :", [r.request_id for r in club])
    print("  max(items)   :", max(club.all_items()).name)

    heading("7. DUCK TYPING: no shared base class needed")
    print("  ConsoleNotifier bases:", [c.__name__ for c in ConsoleNotifier.__mro__[1:]])
    print("  LogNotifier bases    :", [c.__name__ for c in LogNotifier.__mro__[1:]])
    print("  LogNotifier stored", len(log), "notifications")
    try_it("object without send()", lambda: club.add_notifier(object()))
    print_report("Mixed records, one function", [calculator, simon, r1, AdHocRecord()])

    heading("8. MIXIN: to_json() inherited by Item, User and BorrowRequest")
    print(calculator.to_json())

    heading("9. HISTORY (activity 10)")
    for r in club.history_for(simon):
        print("  ", r)
    print("\n  Currently borrowed:", club.currently_borrowed() or "none")


if __name__ == "__main__":
    main() 