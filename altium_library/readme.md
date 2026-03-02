# Theory of operation

These libraries are stored in CSV files, one table per file. Each table has fields that point to specific SchLib and PcbLib files and entries for symbols and footprints. The Windows ODBC system provides a local connection to the files.

Altium uses the dblib file to know what database to use. It also specifies field mappings for each table (CSV file). A user needs to use the "ODBC data sources (64-bit)" tool to get Windows to expose the CSV files as a SQL database.

# Getting started

Under the "User DSN" tab, hit "add", then select "Microsoft Access text driver". Give it the name "solarcar-altium-db", uncheck "use current directory", and select the "tables" directory in this repository. "OK" all the way out of the tool, restart Altium, and ensure that the dblib can connect to the ODBC provider and open the tables.

# Scripts

In the 'scripts' folder are some tools for downloading the JLCPCB library from yaqwsx. It'll come as a multi-part zip containing a sqlite database. The other tool parses that out into various CSV tables for use with Altium.
