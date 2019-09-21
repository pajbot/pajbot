# Scripts

## transfer-\*.sh

`transfer-sql.sh` needs to be configured, modify the `mysql_command` variable at
the top to fit your setup.  
`tranfer-all.sh` needs to have the `streamer_db` function modified to translate
streamer names to their databases.

## emoji-generate

Generates a list of all unicode emoji.

Useful to generate/refresh the `emoji.py` file with fresh data.  
Draws directly from the official unicode `emoji-test.txt` file and generates a
list format that can be inserted into `../pajbot/emoji.py`.

E.g.:

```bash
source venv/bin/activate

# generate new file...
./scripts/emoji-generate.py > ./pajbot/emoji.py

# and reformat it afterwards.
black pajbot
```

## migrate-mysql-to-postgresql

Edit `migrate-mysql-to-postgresql.py` with your connection parameters. Then run `./migrate-mysql-to-postgresql`.

The script takes a fresh PostgreSQL database/schema, creates the database schema, and then copies all data from a MySQL database to the PostgreSQL one.
