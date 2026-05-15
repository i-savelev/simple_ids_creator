from simple_ids_creator.interface import Program


def main() -> int:
    """
    Запустить графический интерфейс приложения.

    :returns: Код завершения процесса.
    """
    program = Program()
    program.initialize()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
