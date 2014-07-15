#


# GmbdApp:
#
class GmbdApp :


    # main:
    #
    @classmethod
    def main (cls) :
        app = cls()
        app.run()


    # run:
    #
    def run (self) :
        print('gmbd: hello')


# exec
if __name__ == '__main__' :
    GmbdApp.main()
