#


# GmbApp:
#
class GmbApp :


    # main:
    #
    @classmethod
    def main (cls) :
        app = cls()
        app.run()


    # run:
    #
    def run (self) :
        print('gmb: hello')


# exec
if __name__ == '__main__' :
    GmbApp.main()
