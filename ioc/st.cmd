#!../../bin/linux-x86_64/softIoc

## Minimal IOC startup script for latency test

epicsEnvSet("EPICS_CA_ADDR_LIST", "0.0.0.0")
epicsEnvSet("EPICS_CAS_INTF_ADDR_LIST", "0.0.0.0")
epicsEnvSet("EPICS_CA_AUTO_ADDR_LIST", "YES")

dbLoadRecords("test.db")

iocInit

## Print loaded PVs
dbl
