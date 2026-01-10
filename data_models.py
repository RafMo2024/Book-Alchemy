
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Defining class Author that inherits from db.Model
class Author(db.Model):
    __tablename__ = 'authors'

    author_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    author_name = db.Column(db.String(200), nullable=False)
    # Specifying a length for String columns. Without a length, different databases handle this differently,
    # which can cause issues. Also adding nullable=False since an author must have a name.
    birth_date = db.Column(db.Date, nullable=False)
    date_of_death = db.Column(db.Date)

    # Adding the relationship to Book class
    books = db.relationship("Book", backref="author", lazy=True)

    def __repr__(self):
        return f"Author(id = {self.author_id}, name = {self.author_name})"

    def __str__(self):
        return f"The id {self.author_id} represents the author {self.author_name}"

# Defining class Books
class Book(db.Model):
    __tablename__ = 'books'

    book_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    isbn = db.Column(db.String(20), unique=True, nullable=False)
    # Adding length constraint db.String(20) and unique=True to prevent duplicate ISBNs in our database.
    # Also, since ISBN is required in our validation, adding nullable=False
    book_title = db.Column(db.String)
    publication_year = db.Column(db.Integer)

    # Foreign Key linking to the Author class
    author_id = db.Column(db.Integer, db.ForeignKey("authors.author_id"), nullable=False)
    # Adding nullable=False since a book must have an author. This enforces data integrity at the database level,
    # not just in our application logic.

    def __repr__(self):
        return f"Book(id = {self.book_id}, title = {self.book_title})"

    def __str__(self):
        return f"The book {self.book_id} is written by {self.author_id}"

