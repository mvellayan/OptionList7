FROM python:3.9.4
COPY requirements.txt /Development/OptionList7/requirements.txt
WORKDIR /Development/OptionList7
RUN pip install -r requirements.txt
COPY . /Development/OptionList7/

# RUN echo 'Docker!' | passwd --stdin root
CMD [ "pull_option_data.sh" ]
