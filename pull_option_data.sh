#!/usr/bin/env bash
# Weekly IB pull. Each step reports timing to a program-details table shown
# in the completion email.

set -u

START_TIME=$(date +%s)
START_TIME_FORMATTED=$(date '+%Y-%m-%d %H:%M:%S')
echo "$START_TIME_FORMATTED: Overall Start"

PROGRAM_DETAILS=""
STEP=0

# run_step <display-name> <command...>
run_step() {
    STEP=$((STEP + 1))
    local name="$1"; shift
    local start_fmt; start_fmt=$(date '+%Y-%m-%d %H:%M:%S')
    local start_sec; start_sec=$(date +%s)
    echo "$(date): Step: $STEP ($name)"

    "$@"
    local rc=$?

    local end_fmt; end_fmt=$(date '+%Y-%m-%d %H:%M:%S')
    local end_sec; end_sec=$(date +%s)
    local dur=$((end_sec - start_sec))
    local min=$((dur / 60))
    local sec=$((dur % 60))
    PROGRAM_DETAILS="${PROGRAM_DETAILS}<tr><td>${STEP}</td><td>${name}</td><td>${start_fmt}</td><td>${end_fmt}</td><td>${min}m ${sec}s</td><td>${rc}</td></tr>"
}

cd ./data-collection
run_step "1dc-pull-option-list.py"       python3 1dc-pull-option-list.py
run_step "2dc-migrate-todo-to-sqlite.py" python3 2dc-migrate-todo-to-sqlite.py
run_step "3dc-plan-tasks.py"             python3 3dc-plan-tasks.py
run_step "4dc-execute-tasks.py"          python3 4dc-execute-tasks.py
cd ../data-prep/
run_step "2p-load-to-mysql.py"           python3 2p-load-to-mysql.py
cd ..

END_TIME=$(date +%s)
END_TIME_FORMATTED=$(date '+%Y-%m-%d %H:%M:%S')
DURATION=$((END_TIME - START_TIME))
HOURS=$((DURATION / 3600))
MINUTES=$(((DURATION % 3600) / 60))
SECONDS=$((DURATION % 60))

EMAIL_BODY="<html><body><h3>OptionList7 Completed</h3><h4>Overall Summary</h4><table border='1' cellpadding='8' cellspacing='0' style='border-collapse: collapse; font-family: Arial, sans-serif; margin-bottom: 20px;'><tr style='background-color: #f2f2f2;'><th>Metric</th><th>Value</th></tr><tr><td><strong>Start Time</strong></td><td>$START_TIME_FORMATTED</td></tr><tr><td><strong>End Time</strong></td><td>$END_TIME_FORMATTED</td></tr><tr><td><strong>Duration</strong></td><td>${HOURS}h ${MINUTES}m ${SECONDS}s</td></tr></table><h4>Program Details</h4><table border='1' cellpadding='8' cellspacing='0' style='border-collapse: collapse; font-family: Arial, sans-serif;'><tr style='background-color: #f2f2f2;'><th>Step</th><th>Program Name</th><th>Start Time</th><th>End Time</th><th>Duration</th><th>Return Code</th></tr>$PROGRAM_DETAILS</table></body></html>"

aws ses send-email --to "muthu.vellayan@gmail.com" --html "$EMAIL_BODY" --from muthu.vellayan@nayalle.com --subject "OptionList 7 Completed..."
echo "$(date): Done!"
