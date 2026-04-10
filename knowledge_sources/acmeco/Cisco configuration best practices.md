
## Interface descriptions mandatory convention

Rule #1 Every interface where an edge device (e.g. linux or windows server) is should have a description in the following format:

"edge-YYYY-MM-DD-last-configurtion", where YYYY-MM-DD are year-month-day of the last configuration change on this interface

Rule #2 Every interface that is transit between two network interfaces should have a description in configuration with the following format:

"transit-to-XXXX",  where XXXX should be replaced with a hostname of neighboring device