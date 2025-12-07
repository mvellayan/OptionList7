START_TIME=$(date +%s)
START_TIME_FORMATTED=$(date '+%Y-%m-%d %H:%M:%S')
echo $START_TIME_FORMATTED: Overall Start

# Initialize program details array
PROGRAM_DETAILS=""

# Program 1
echo `date`: Step: 1
PROG1_START=$(date '+%Y-%m-%d %H:%M:%S')
PROG1_START_SEC=$(date +%s)
cd ./data-collection
python3 1dc-pull-option-list.py
PROG1_RC=$?
PROG1_END=$(date '+%Y-%m-%d %H:%M:%S')
PROG1_END_SEC=$(date +%s)
PROG1_DURATION=$((PROG1_END_SEC - PROG1_START_SEC))
PROG1_MIN=$((PROG1_DURATION / 60))
PROG1_SEC=$((PROG1_DURATION % 60))
PROGRAM_DETAILS="${PROGRAM_DETAILS}<tr><td>1</td><td>1dc-pull-option-list.py</td><td>$PROG1_START</td><td>$PROG1_END</td><td>${PROG1_MIN}m ${PROG1_SEC}s</td><td>$PROG1_RC</td></tr>"

# Program 2
echo `date`: Step: 2
PROG2_START=$(date '+%Y-%m-%d %H:%M:%S')
PROG2_START_SEC=$(date +%s)
python3 3dc-plan-tasks.py
PROG2_RC=$?
PROG2_END=$(date '+%Y-%m-%d %H:%M:%S')
PROG2_END_SEC=$(date +%s)
PROG2_DURATION=$((PROG2_END_SEC - PROG2_START_SEC))
PROG2_MIN=$((PROG2_DURATION / 60))
PROG2_SEC=$((PROG2_DURATION % 60))
PROGRAM_DETAILS="${PROGRAM_DETAILS}<tr><td>2</td><td>3dc-plan-tasks.py</td><td>$PROG2_START</td><td>$PROG2_END</td><td>${PROG2_MIN}m ${PROG2_SEC}s</td><td>$PROG2_RC</td></tr>"

# Program 3
echo `date`: step: 3
PROG3_START=$(date '+%Y-%m-%d %H:%M:%S')
PROG3_START_SEC=$(date +%s)
python3 4dc-execute-tasks.py
PROG3_RC=$?
PROG3_END=$(date '+%Y-%m-%d %H:%M:%S')
PROG3_END_SEC=$(date +%s)
PROG3_DURATION=$((PROG3_END_SEC - PROG3_START_SEC))
PROG3_MIN=$((PROG3_DURATION / 60))
PROG3_SEC=$((PROG3_DURATION % 60))
PROGRAM_DETAILS="${PROGRAM_DETAILS}<tr><td>3</td><td>4dc-execute-tasks.py</td><td>$PROG3_START</td><td>$PROG3_END</td><td>${PROG3_MIN}m ${PROG3_SEC}s</td><td>$PROG3_RC</td></tr>"

cd ../data-prep/

# Program 4
echo `date`: step: 4
PROG4_START=$(date '+%Y-%m-%d %H:%M:%S')
PROG4_START_SEC=$(date +%s)
python3 1p-project-join.py
PROG4_RC=$?
PROG4_END=$(date '+%Y-%m-%d %H:%M:%S')
PROG4_END_SEC=$(date +%s)
PROG4_DURATION=$((PROG4_END_SEC - PROG4_START_SEC))
PROG4_MIN=$((PROG4_DURATION / 60))
PROG4_SEC=$((PROG4_DURATION % 60))
PROGRAM_DETAILS="${PROGRAM_DETAILS}<tr><td>4</td><td>1p-project-join.py</td><td>$PROG4_START</td><td>$PROG4_END</td><td>${PROG4_MIN}m ${PROG4_SEC}s</td><td>$PROG4_RC</td></tr>"

# Program 5
echo `date`: step: 5
PROG5_START=$(date '+%Y-%m-%d %H:%M:%S')
PROG5_START_SEC=$(date +%s)
python3 2p-load-to-mysql.py
PROG5_RC=$?
PROG5_END=$(date '+%Y-%m-%d %H:%M:%S')
PROG5_END_SEC=$(date +%s)
PROG5_DURATION=$((PROG5_END_SEC - PROG5_START_SEC))
PROG5_MIN=$((PROG5_DURATION / 60))
PROG5_SEC=$((PROG5_DURATION % 60))
PROGRAM_DETAILS="${PROGRAM_DETAILS}<tr><td>5</td><td>2p-load-to-mysql.py</td><td>$PROG5_START</td><td>$PROG5_END</td><td>${PROG5_MIN}m ${PROG5_SEC}s</td><td>$PROG5_RC</td></tr>"

cd ..

END_TIME=$(date +%s)
END_TIME_FORMATTED=$(date '+%Y-%m-%d %H:%M:%S')
DURATION=$((END_TIME - START_TIME))
HOURS=$((DURATION / 3600))
MINUTES=$(((DURATION % 3600) / 60))
SECONDS=$((DURATION % 60))

EMAIL_BODY="<html><body><h3>OptionList7 Completed</h3><h4>Overall Summary</h4><table border='1' cellpadding='8' cellspacing='0' style='border-collapse: collapse; font-family: Arial, sans-serif; margin-bottom: 20px;'><tr style='background-color: #f2f2f2;'><th>Metric</th><th>Value</th></tr><tr><td><strong>Start Time</strong></td><td>$START_TIME_FORMATTED</td></tr><tr><td><strong>End Time</strong></td><td>$END_TIME_FORMATTED</td></tr><tr><td><strong>Duration</strong></td><td>${HOURS}h ${MINUTES}m ${SECONDS}s</td></tr></table><h4>Program Details</h4><table border='1' cellpadding='8' cellspacing='0' style='border-collapse: collapse; font-family: Arial, sans-serif;'><tr style='background-color: #f2f2f2;'><th>Step</th><th>Program Name</th><th>Start Time</th><th>End Time</th><th>Duration</th><th>Return Code</th></tr>$PROGRAM_DETAILS</table></body></html>"

aws ses send-email --to "muthu.vellayan@gmail.com" --html "$EMAIL_BODY" --from muthu.vellayan@nayalle.com --subject "OptionList 7 Completed..."
echo `date`: Done!
