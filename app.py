from flask import Flask, request, render_template, redirect, url_for, flash
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload
from datetime import datetime, date

from data_models import db, Author, Book
import os

app = Flask(__name__)

app.secret_key = os.environ.get('SECRET_KEY', 'dev-key-only')

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(basedir, 'data/library.sqlite')}"

db.init_app(app)


@app.route('/')
def index():
    """Redirects the root URL to the home page to avoid 404 errors."""
    return redirect(url_for('home'))


@app.route('/add_author', methods=['GET', 'POST'])
def add_author():
    """This method adds authors to the database by rendering an HTML page connected through Flask app"""
    if request.method == "POST":
        author_name = request.form.get("name")
        birth_date_str = request.form.get("birthdate")
        date_of_death_str = request.form.get("date_of_death")  # optional

        # Validation: Required fields
        if not author_name or not birth_date_str:
            return render_template("add_author.html", message="Invalid author data. Name and birthdate required.")

        # Validation: Check if author already exists
        if Author.query.filter_by(author_name=author_name).first():
            return render_template("add_author.html", message=f"Author '{author_name}' already exists.")

        # Convert string to date object
        try:
            birth_date = datetime.strptime(birth_date_str, "%Y-%m-%d").date()
        except ValueError:
            return render_template("add_author.html", message="Invalid date format")

        # Validation: Birth date cannot be in the future
        if birth_date > date.today():
             return render_template("add_author.html", message="Birth date cannot be in the future.")

        # Handle date_of_death
        if date_of_death_str:
            try:
                date_of_death = datetime.strptime(date_of_death_str, "%Y-%m-%d").date()
                # Validation: Death date logic
                if date_of_death < birth_date:
                    return render_template("add_author.html", message="Date of death cannot be before birth date.")
                if date_of_death > date.today():
                    return render_template("add_author.html", message="Date of death cannot be in the future.")
            except ValueError:
                return render_template("add_author.html", message="Invalid death date format")
        else:
            date_of_death = None

        # Creating an author object
        author = Author(
            author_name=author_name,
            birth_date=birth_date,
            date_of_death=date_of_death
        )

        # Adding and commiting to the database
        db.session.add(author)
        try:
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            return render_template("add_author.html", message="Database error")

        return render_template("add_author.html", message=f"Author '{author_name}' added successfully!")

    return render_template('add_author.html')


@app.route('/add_book', methods=['GET', 'POST'])
def add_book():
    """This method adds books to the database by rendering an HTML page connected through Flask app"""
    if request.method == "POST":
        title = request.form.get("title")
        isbn = request.form.get("isbn")

        publication_year = request.form.get("publication_year") or None
        author_name = request.form.get("author_name") or None

        # Validation: Check required fields
        if not title or not isbn:
            return render_template("add_book.html", message="Invalid book data. Title and isbn required.")

        # Validation: Check if book with this ISBN already exists
        if Book.query.filter_by(isbn=isbn).first():
             return render_template("add_book.html", message=f"A book with ISBN {isbn} already exists.")

        # Linking the author
        author = Author.query.filter_by(author_name=author_name).first()

        if not author:
            return f"Author '{author_name}' not found in the Database. Please add the author first.", 400

        # Creating a book object
        book = Book(
            book_title=title,
            isbn=isbn,
            publication_year=publication_year,
            author_id=author.author_id
        )

        db.session.add(book)
        try:
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            return render_template("add_book.html", message="Database error")

        return render_template("add_book.html", message=f"Book '{book.book_title}' added successfully!")

    return render_template('add_book.html')


def get_cover_url(isbn, size="M"):
    """
    This functions returns the cover image URL from Open Library for a given ISBN.
    size can be: S, M, L (small, medium, large) but we have set the default value to be M.
    """
    if not isbn:
        return None
    return f"https://covers.openlibrary.org/b/isbn/{isbn}-{size}.jpg"


@app.route('/home')
def home():
    """
    Renders the home page displaying all books.
    Supports searching by query parameter 'q' and sorting by 'sort' parameter (title or author).
    """
    sort_by = request.args.get("sort")
    search_term = request.args.get("q")

    # Base query with joined load for performance
    query = Book.query.options(joinedload(Book.author))

    # Search functionality
    if search_term:
        books = query.join(Author).filter(
            or_(
                Book.book_title.ilike(f"%{search_term}%"),
                Author.author_name.ilike(f"%{search_term}%")
            )
        ).all()
    # Sorting functionality
    elif sort_by == "title":
        books = query.order_by(Book.book_title).all()
    elif sort_by == "author":
        books = query.join(Author).order_by(Author.author_name).all()
    else:
        books = query.all()

    # Prepare data for template
    books_with_covers = []
    for book in books:
        books_with_covers.append({
            "id": book.book_id,
            "title": book.book_title,
            "isbn": book.isbn,
            "year": book.publication_year,
            "author_name": book.author.author_name,
            "cover_url": get_cover_url(book.isbn),
        })

    return render_template('home.html', books=books_with_covers)


@app.route('/book/<int:book_id>/delete', methods=['POST', 'DELETE'])
def delete_book(book_id):
    """
    Deletes a specific book based on its ID.
    If the author has no other books left, the author is also deleted.
    """
    book = Book.query.get(book_id)

    if not book:
        flash(f"Book with ID {book_id} does not exist.", "error")
        return redirect(url_for("home"))

    # Prepare data for message before deletion
    book_title = book.book_title
    author = book.author

    db.session.delete(book)
    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        flash("Database error during book deletion", "error")
        return redirect(url_for("home"))

    # Check if author has other books
    if not author.books:
        author_name = author.author_name
        db.session.delete(author)
        try:
            db.session.commit()
            flash(f"Book '{book_title}' and its author '{author_name}' deleted successfully.", "success")
        except SQLAlchemyError:
            db.session.rollback()
            flash("Database error during author deletion", "error")
            return redirect(url_for("home"))
    else:
        flash(f"Book '{book_title}' deleted successfully.", "success")

    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=True)