import typer
from app.database import create_db_and_tables, get_session, drop_all
from app.models import User
from fastapi import Depends
from sqlmodel import select
from sqlalchemy.exc import IntegrityError

cli = typer.Typer()

@cli.command()
def initialize():
    """Reset the database: drop all tables and recreate them.

    This command inserts a sample user (`bob`) after creating tables.
    """
    with get_session() as db: # Get a connection to the database
        drop_all() # delete all tables
        create_db_and_tables() #recreate all tables
        bob = User('bob', 'bob@mail.com', 'bobpass') # Create a new user (in memory)
        db.add(bob) # Tell the database about this new data
        db.commit() # Tell the database persist the data
        db.refresh(bob) # Update the user (we use this to get the ID from the db)
        print("Database Initialized")

@cli.command()
def get_user(query: str = typer.Argument(..., help="Partial username or email to search for")):
    """Find users where username OR email partially matches `query`.

    Example: `get-user em` matches `emily` and `em@example.com`.
    """
    with get_session() as db: # Get a connection to the database
        stmt = select(User).where(
            (User.username.contains(query)) | (User.email.contains(query))
        )
        users = db.exec(stmt).all()
        if not users:
            print("No users found")
            return
        for u in users:
            print(u)

@cli.command()
def get_all_users(
    limit: int = typer.Option(10, help="Maximum number of users to return."),
    offset: int = typer.Option(0, help="Number of users to skip (for pagination)."),
):
    """List users with pagination.

    Use `--limit` to control page size and `--offset` to skip rows.
    """
    with get_session() as db:
        stmt = select(User).offset(offset).limit(limit)
        users = db.exec(stmt).all()
        if not users:
            print("No users found")
            return
        for u in users:
            print(u)



@cli.command()
def change_email(
    username: str = typer.Argument(..., help="Username of the user to update."),
    new_email: str = typer.Argument(..., help="New email address to set."),
):
    """Change the email address for a user identified by `username`."""
    with get_session() as db: # Get a connection to the database
        user = db.exec(select(User).where(User.username == username)).first()
        if not user:
            print(f'{username} not found! Unable to update email.')
            return
        user.email = new_email
        db.add(user)
        db.commit()
        print(f"Updated {user.username}'s email to {user.email}")

@cli.command()
def create_user(
    username: str = typer.Argument(..., help="Desired username for the new user."),
    email: str = typer.Argument(..., help="Email address for the new user."),
    password: str = typer.Argument(..., help="Plain-text password for the new user."),
):
    """Create a new user with `username`, `email`, and `password`.

    Passwords are hashed before storage.
    """
    with get_session() as db: # Get a connection to the database
        newuser = User(username, email, password)
        try:
            db.add(newuser)
            db.commit()
        except IntegrityError as e:
            db.rollback() #let the database undo any previous steps of a transaction
            print("Username or email already taken!") #give the user a useful message
        else:
            print(newuser) # print the newly created user

@cli.command()
def delete_user(username: str = typer.Argument(..., help="Username of the user to delete.")):
    """Delete a user by `username`. This action is irreversible."""
    with get_session() as db:
        user = db.exec(select(User).where(User.username == username)).first()
        if not user:
            print(f'{username} not found! Unable to delete user.')
            return
        db.delete(user)
        db.commit()
        print(f'{username} deleted')


if __name__ == "__main__":
    cli()