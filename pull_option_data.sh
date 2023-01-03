#cd ~/Development/OptionList7/
#source ./bin/activate
echo `date`: Step: 1
cd ./data-collection
echo `date`: Step: 2
python3 1dc-pull-option-list.py
echo `date`: Step: 3 
python3 3dc-plan-tasks.py
echo `date`: step: 4
python3  4dc-execute-tasks.py


cd ../data-prep/
echo `date`: step: 5
python3 1p-project-join.py	
echo `date`: step: 6
python3 2p-load-to-mysql.py
echo `date`: Done!
