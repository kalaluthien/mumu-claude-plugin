<!-- Deliberately weakened copy of technical-sqlite.md: same headings, sections, paragraphs, facts and examples; weakened in language only. -->
# Appropriate Uses For SQLite

Direct comparability of SQLite with client/server SQL database engines such as MySQL, Oracle, PostgreSQL, or SQL Server is not possible, since a different problem is being solved by it.

The implementation of a shared repository of enterprise data is striven for by client/server SQL database engines, with emphasis being placed on scalability, concurrency, centralization, and control, whereas the provision of local data storage for individual applications and devices is what is striven for by the embedded engine, and economy, efficiency, reliability, independence, and simplicity are emphasized by it.

Competition with client/server databases is not engaged in by the library, it competes with `fopen()`.

## 1. Situations Where SQLite Works Well

### Embedded devices and the internet of things

Because no administration is required by an SQLite database, it works well in devices where operation without expert human support is necessary, and a good fit is represented by it for utilization in cellphones, set-top boxes, televisions, game consoles, cameras, watches, kitchen appliances, thermostats, automobiles, machine tools, airplanes, remote sensors, drones, medical devices, and robots, i.e. the "internet of things".

Client/server database engines have been designed for residence inside a lovingly-attended datacenter at the core of the network, and it works there too, but thriving at the edge of the network is also achieved by the DB, where it fends for itself while fast and reliable data services are provided to applications whose connectivity would otherwise be dodgy.

### Application file format

Frequent use of SQLite is made as the on-disk file format for desktop applications such as version control systems, financial analysis tools, media cataloging and editing suites, CAD packages, record keeping programs, and so forth, with attachment to the database file being performed by the traditional File/Open operation via a call to `sqlite3_open()`, and since updates happen automatically as revision of application content occurs, this makes the File/Save menu option superfluous, while implementation of the File/Save_As menu option can be achieved using the [backup API](https://www.sqlite.org/backup.html).

Many benefits are associated with this, including improvements in performance, reductions in cost and complexity, and improvement of reliability, and for more information technical notes ["aff_short.html"](https://www.sqlite.org/aff_short.html) and ["appfileformat.html"](https://www.sqlite.org/appfileformat.html) and ["fasterthanfs.html"](https://www.sqlite.org/fasterthanfs.html) should be seen, it being closely related to the data transfer format and data container use cases below.

### Websites

The engine works great as the database engine for most low to medium traffic websites (which is to say, most websites), though the amount of web traffic handleable by it is dependent on the heaviness of the website's utilization of its database, and generally speaking fine operation should be expected for any site receiving fewer than 100K hits/day, this figure being a conservative estimate rather than a hard upper bound, with operation at 10 times that amount of traffic having been demonstrated.

The website of the library (https://sqlite.org/) uses it itself, of course, and as of this writing (2015) about 400K to 500K HTTP requests per day are handled by it, of which about 15-20% are dynamic pages touching the DB, with about 200 SQL statements per webpage being used by dynamic content, and this runs on a single VM that shares a physical server with 23 others while the load average is still kept below 0.1 most of the time.

### Data analysis

Employment of the sqlite3 CLI REPL (or various third-party SQLite access programs) for the analysis of large datasets can be undertaken by people with an understanding of SQL, whereby the importation of raw data from CSV files is performed and then it can be sliced and diced for the generation of a myriad of summary reports, while more complex analysis can be done via simple scripts written in Tcl or Python (both of which come with the engine built-in) or in R or other languages by means of readily available FFI adaptors, and possible uses include website log analysis, sports statistics analysis, compilation of programming metrics, and analysis of experimental results, it being used in this way by many bioinformatics researchers.

The same thing can be done with an enterprise client/server database, of course, but the advantage of the library is the greater ease of installation and use, and the resulting artefact is a single file for which writing to a USB memory stick or emailing to a colleague is possible.

### Cache for enterprise data

Many applications make use of the DB as a cache of relevant content from an enterprise RDBMS, which brings a reduction of latency, since most queries now occur against the local cache with avoidance of a network round-trip, and a reduction of the load on the network and on the central database server is also brought by it, and in many cases continued operation of the client-side application during network outages is meant by this.

### Server-side database

Success has been reported by systems designers with the utilization of SQLite as a data store on server applications running in the datacenter, or in other words, as the underlying storage engine for an application-specific database server, i.e. the persistence tier.

With this, the overall system is still client/server, with requests being sent by clients to the server and replies being gotten back over the network, but instead of generic SQL being sent and raw table content being returned, high-level and application-specific requests and responses are exchanged, and the translation of requests into multiple SQL queries, the gathering of the results, the performance of post-processing, filtering, and analysis, and then the construction of a high-level reply containing only the essential information is carried out by it.
