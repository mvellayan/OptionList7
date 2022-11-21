import datetime
import common.ol_pd as olpd
import common.ol_util as olu


def main():

    print("_____________________________________________________")
    print("  PATH:", olu.FILE_GROUPS)
    df = olpd.load_data(olu.FILE_GROUPS)
    df = olu.dedup(df, 390)
    print("_____________________________________________________")


start_time = datetime.datetime.now()
main()
print("\n\nStarted: ", start_time, ' Finished: ', datetime.datetime.now(), ' Dur: ', (datetime.datetime.now() - start_time).total_seconds())
print(olu.tn() + "2-report-missing-data done!")