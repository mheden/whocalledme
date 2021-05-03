# Who Called Me?

A basic tool for showing the callgraph to one function for c code projects.

## Usage

1) Add the flag `-fdump-rtl-expand` to the GCC command line wich emits RTL files ending in `.expand`

2) Add the `.expand` file data to a database
   ```bash
   wcm_create_db.py database.db folder1/*.expand folder2/*.expand...
   ```

3) Query the database by running `wcm.py`. The is using `fzf` to be able to do "fuzzy finding" of the variable

## Links

[Developer Options (Using the GNU Compiler Collection (GCC))](https://gcc.gnu.org/onlinedocs/gcc/Developer-Options.html)

[RTL (GNU Compiler Collection (GCC) Internals)](https://gcc.gnu.org/onlinedocs/gccint/RTL.html)
