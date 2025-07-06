# STORE LINK
#### Video Demo:  <URL HERE>
#### Description:

STORE LINK (I wanted to come with a creative name) is a simple web application that solves a problem I constantly face: having way too many browser tabs open! Instead of bookmarking sites and forgetting about them, or losing interesting links in the chaos of my browser, this app gives me a clean, simple way to save and organize links without the hassle of complex folder structures or categories that some other competitors offer.

## What This Project Does

This web application allows users to create an account, log in, and save interesting links to a personal dashboard. The focus is on **simplicity** - no complicated organization systems or folders, just a straightforward way to store links with optional descriptions and see them organized by date. Each saved link gets its own card with a preview image.

## Project Architecture

The application follows a simple Flask-based architecture with the following key components:

### `app.py` 

This is the main Flask application file that handles all the routing, user authentication, and database operations. It manages user sessions, processes form submissions, and coordinates between the frontend templates and the backend database. The file includes routes for registration, login, dashboard management, and and operations for creating, editing, and deleting links.

### Database Design

I'm using SQLAlchemy for database management, which was a learning experience in itself. Initially, I made a crucial mistake in my database design - I had set it up so that any user could see any other user's saved links, which obviously isn't what we want for a personal link manager! I had to redesign the database schema to properly associate links with specific users through foreign keys, ensuring data privacy.

Here's the database schema:

```sql
CREATE TABLE user (
        id INTEGER NOT NULL, 
        email VARCHAR(120) NOT NULL, 
        hash VARCHAR(128) NOT NULL, 
        PRIMARY KEY (id), 
        UNIQUE (email)
);

CREATE TABLE link (
        id INTEGER NOT NULL, 
        url VARCHAR(500) NOT NULL, 
        title VARCHAR(300) NOT NULL, 
        preview_url VARCHAR(500) NOT NULL, 
        comment VARCHAR(500), 
        timestamp DATETIME, 
        user_id INTEGER, 
        PRIMARY KEY (id)
);
```

### Templates Directory

**`base.html`** - This is the foundation template that uses Jinja2 templating (similar to what we used in CS50's pset9). It contains the common HTML structure, navigation, and styling that all other pages inherit from. I added Google's Material Design icons and also created favicons.

**`landing.html`** - I decided to create a dedicated landing page to showcase the benefits of the application. This page doesn't use the base.html. I had some difficulties with the header when user was logged-in, so decided to make it separate. There's room to add screenshots or feature highlights in the future.

**`login.html` and `signup.html`** - These contain simple forms for user authentication. I added error handling: if a user enters a password which is too short, the website won't allow the user to sign up. I also used notification method with get_flashed_messages.

**`dashboard.html`** - This is the main interface where users manage their links. It features:

- A form at the top where users can paste a URL and add an optional description
- Link cards organized chronologically by date added
- Each card shows a preview image (when available), the link title, URL, description, and date. If there's no preview, I added a placeholder image in the img folder
- Quick action buttons for editing and deleting links

**`edit.html`** - A dedicated page for modifying saved links. Users can update the URL or change the description. I chose to make this a separate page to avoid JavaScript.

**`404.html` and `500.html`** - Custom error pages. Just because they should be in a project. Just a simple message and buttons to go back.

## Design Challenges

### CSS Management

One of the biggest challenges was managing the CSS. I got help from Claude AI, but I found that it often overcomplicated simple styling tasks. Nevertheless, AI helped me especially with media queries and overall design, but then I manually tweaked the code myself.

### What I Learned

The database privacy issue I mentioned earlier was a real learning experience. It taught me the importance of thinking through data relationships from the start and the security implications of database design. Fixing it required understanding foreign keys, user sessions, and query filtering.

## Future Plans

I have several ideas for expanding this project:

1. **Email/Telegram Digest Feature**: Send users a weekly digest of their saved links via email or Telegram.

2. **Tagging System**: Add the ability to tag links with keywords for better organization.

3. **Link Validation**: Check if saved links are still active and notify users of broken links.

4. **Import/Export**: Allow users to import bookmarks from browsers or export their link collection.

## Why This Project Matters

This isn't just a CS50 assignment - it's solving a real problem I have. Building something you actually want to use makes the development process more engaging. The project taught me about full-stack web development, database design, user authentication and basic knowledge how to deploy projects. 
I'm working as a UX designer and this knowledge is already helping me to understand better the development process.
