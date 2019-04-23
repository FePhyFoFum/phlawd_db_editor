# phlawd_db_editor

This houses some basic commands for making edits to the taxonomy in [phlawd_db_maker](https://github.com/blackrim/phlawd_db_maker) databases.

The basic commands are

- info   : `-i NCBIID or NAME`
- create : `-c NAME PARENTNCBIID RANK`
- delete : `-d NCBIID`
- move   : `-m NCBIID PARENTNCBIID RANK`
- rename : `-r NCBIID NEWNAME`

Only do one at a time and be careful! Delete and move edits can also take names as arguments, although this only works if names are unique (this is checked). Each edit will be stored in a logfile (which you can set with `-l` or it defaults to `phlawd_db_editor.log`).

Once you have completed your edits, you will need to `--rebuild`. 

## Things that are not completed yet

Right now, this is safe for higher taxa that are not likely to have sequences associated. If you expect the taxa that you are fussing with to have sequences associated, that has not been implemented yet. If it hasn't by the time you need it, just create an issue and I will tackle it then.