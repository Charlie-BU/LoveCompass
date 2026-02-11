from robyn import Robyn

from server.faas import start_faas_server


def main():
    app = Robyn(__file__)
    start_faas_server(app)


if __name__ == "__main__":
    main()
