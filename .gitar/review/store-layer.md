# Store layer

Route handlers under `app/routes/` never query the database directly. All data access goes through the `Store` interface in `app/store.py` (`MemoryStore` for tests, `PostgresStore` for deployments).

Flag, as an important issue, any route handler that:

- imports `psycopg` or any other database driver or ORM,
- opens a database connection or cursor, or executes SQL, even when the connection URL comes from `DATABASE_URL`,
- reads private attributes of the store (such as `store._url`) to run its own queries.

When a handler needs a query the Store does not offer yet (an aggregate, for example), the fix is to add a method to the `Store` protocol, implement it in both `MemoryStore` and `PostgresStore`, and call it from the handler. SQL lives in `app/store_pg.py` only.
