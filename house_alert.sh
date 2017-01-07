#!/bin/bash

function collectDiffs {
    DIR=$1
    REPORTFILE=$2

    # Diff the results
    CURRENT=`ls -rt $DIR/*-results.txt | tail -n2 | tail -n1`
    RECENT=`ls -rt $DIR/*-results.txt | tail -n2 | head -n1`
    diff $RECENT $CURRENT
    if [ "$?" -ne "0" ]; then
        echo "============= DIFF FOR $DIR RESULTS =============" >> $REPORTFILE
        diff -U40 $RECENT $CURRENT >> $REPORTFILE
        echo "============= END DIFF FOR $DIR RESULTS =============" >> $REPORTFILE
    fi

    # Diff the error log
    CURRENT=`ls -rt $DIR/*-errors.txt | tail -n2 | tail -n1`
    RECENT=`ls -rt $DIR/*-errors.txt | tail -n2 | head -n1`
    diff $RECENT $CURRENT
    if [ "$?" -ne "0" ]; then
        echo "============= DIFF FOR $DIR ERRORS =============" >> $REPORTFILE
        diff -U40 $RECENT $CURRENT >> $REPORTFILE
        echo "============= END DIFF FOR $DIR ERRORS =============" >> $REPORTFILE
    fi
}

NOW=`date +"%y-%m-%d-%H-%M-%S"`
mkdir -p reports
EMAIL_REPORT_FILE="reports/$NOW-report.txt"

# house close to sunnyvale caltrain station
DIR="sunnyvale_caltrain"
mkdir -p $DIR
python mls_scraper.py -c 94085,94086,94087 -l "37.3784054,-122.0308731" -t Townhouse,Condominium,Triplex,Fourplex -e -d 1 -p 2000000 -f "$DIR/$NOW-results.txt" "sunnyvale" 2> "$DIR/$NOW-errors.txt"
collectDiffs $DIR $EMAIL_REPORT_FILE

# sunnyvale in-law units
DIR="sunnyvale_inlaw"
mkdir -p $DIR
python mls_scraper.py -c 94085,94086,94087 -t Townhouse,Condominium,Triplex,Fourplex -e -z "R0,R1,R1AB,R-1,SU" -x -s 5000 -p 2000000 -f "$DIR/$NOW-results.txt" "sunnyvale" 2> "$DIR/$NOW-errors.txt"
collectDiffs $DIR $EMAIL_REPORT_FILE

# santaclara in-law units
DIR="santaclara_inlaw"
mkdir -p $DIR
python mls_scraper.py -c 95051,95054,95055 -t Townhouse,Condominium,Triplex,Fourplex -e -s 7000 -p 2000000 -f "$DIR/$NOW-results.txt" "santa clara" 2> "$DIR/$NOW-errors.txt"
collectDiffs $DIR $EMAIL_REPORT_FILE

# cheap houses
DIR="cheap"
mkdir -p $DIR
python mls_scraper.py -c 94085,94086,94087,95051,95054,95055 -t Townhouse,Condominium,Triplex,Fourplex -e -p 1000000 -f "$DIR/$NOW-results.txt" "" 2> "$DIR/$NOW-errors.txt"
collectDiffs $DIR $EMAIL_REPORT_FILE

# lynbrook houses
DIR="lynbrook"
mkdir -p $DIR
python mls_scraper.py -c 95129,95070 -p 1200000 -g "Lynbrook" -f "$DIR/$NOW-results.txt" "" 2> "$DIR/$NOW-errors.txt"
collectDiffs $DIR $EMAIL_REPORT_FILE

# monta vista houses
DIR="montavista"
mkdir -p $DIR
python mls_scraper.py -p 1200000 -g "Monta Vista" -f "$DIR/$NOW-results.txt" "cupertino" 2> "$DIR/$NOW-errors.txt"
collectDiffs $DIR $EMAIL_REPORT_FILE

if [ -f $EMAIL_REPORT_FILE ]; then
    # SEND EMAIL REPORT
    mail -s "NEW HOUSING CHANGE" bhh1988@gmail.com < $EMAIL_REPORT_FILE
fi
