import json
import os
import sys

# Fix encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

sys.dont_write_bytecode = True

from python_parser import BankTransactionParser

# Try to import pytest, but don't fail if it's not installed
try:
    import pytest
    PYTEST_AVAILABLE = True
except ImportError:
    PYTEST_AVAILABLE = False


# Only create pytest fixture if pytest is available
if PYTEST_AVAILABLE:
    @pytest.fixture
    def parser():
        """Create a parser instance for testing."""
        return BankTransactionParser()


def test_parser_universality(parser=None):
    """Test that parser handles various keyword variations."""
    if parser is None:
        parser = BankTransactionParser()
    
    test_cases = [
        {
            "content": "Perekaz: TEST123 na sumu 100.00UAH. Dostupno 500.00UAH.",
            "expected_type": "in",
            "expected_amount": 100.0,
            "expected_currency": "UAH",
            "expected_balance": 500.0
        },
        {
            "content": "Надходження: 200.0UAH",
            "expected_type": "in",
            "expected_amount": 200.0,
            "expected_currency": "UAH",
            "expected_balance": None
        },
        {
            "content": "Баланс: 1000.00 UAH",
            "expected_type": "balance_info",
            "expected_amount": None,
            "expected_currency": None,
            "expected_balance": 1000.0
        },
        {
            "content": "Blokuvannia: MERCHANT Suma 50.00UAH. Dostupno 950.00UAH.",
            "expected_type": "reject",
            "expected_amount": 50.0,
            "expected_currency": "UAH",
            "expected_balance": 950.0
        },
        {
            "content": "Блокування: TEST Suma 75.00UAH. Доступно 925.00UAH.",
            "expected_type": "reject",
            "expected_amount": 75.0,
            "expected_currency": "UAH",
            "expected_balance": 925.0
        },
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        content = test_case["content"]
        result = parser.parse(content)
        
        print(f"\nТест {i}: {content[:50]}...")
        print(f"  Ожидаемый тип: {test_case['expected_type']}")
        print(f"  Полученный тип: {result['operation_type']}")
        
        assert result["operation_type"] == test_case["expected_type"], \
            f"Тест {i}: Неверный тип операции. Вход: {content}"
        
        if test_case["expected_amount"] is not None:
            print(f"  Ожидаемая сумма: {test_case['expected_amount']}")
            print(f"  Полученная сумма: {result['operation_amount']}")
            assert result["operation_amount"] == test_case["expected_amount"], \
                f"Тест {i}: Неверная сумма операции. Вход: {content}"
        
        if test_case["expected_currency"] is not None:
            assert result["operation_currency"] == test_case["expected_currency"], \
                f"Тест {i}: Неверная валюта операции. Вход: {content}"
        
        if test_case["expected_balance"] is not None:
            assert result["bank_account_balance"] == test_case["expected_balance"], \
                f"Тест {i}: Неверный баланс. Вход: {content}"
        
        print(f"  ✓ Тест {i} пройден")


def test_test_case_examples(parser=None):
    """Test parsing all examples from test_case.txt."""
    if parser is None:
        parser = BankTransactionParser()
    
    # Get directory where script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    test_case_path = os.path.join(script_dir, 'test_case.txt')
    
    if not os.path.exists(test_case_path):
        print(f"✗ Файл test_case.txt не найден в {script_dir}")
        return
    
    examples = parse_test_case_file(test_case_path)
    assert len(examples) == 5, f"Ожидалось 5 примеров, найдено {len(examples)}"
    
    expected_results = [
        {
            "operation_type": "in",
            "operation_amount": 1000.0,
            "operation_currency": "UAH",
            "bank_account_balance": 1154.16,
            "bank_account_currency": "UAH",
            "bank_account_details": "000000****0000",
            "counterparty_details": "CLIENT001"
        },
        {
            "operation_type": "in",
            "operation_amount": 2000.0,
            "operation_currency": "UAH",
            "bank_account_balance": 2000.0,
            "bank_account_currency": "UAH",
            "bank_account_details": "*0000",
            "counterparty_details": "CLIENT NAME"
        },
        {
            "operation_type": "balance_info",
            "operation_amount": None,
            "operation_currency": None,
            "bank_account_balance": 5853.79,
            "bank_account_currency": "UAH",
            "bank_account_details": "*0000",
            "counterparty_details": None
        },
        {
            "operation_type": "reject",
            "operation_amount": 2540.43,
            "operation_currency": "UAH",
            "bank_account_balance": 78126.18,
            "bank_account_currency": "UAH",
            "bank_account_details": "000000****0000",
            "counterparty_details": "ORDER001 PAYMENT*MERCHANT"
        },
        {
            "operation_type": "out",
            "operation_amount": 1000.0,
            "operation_currency": "UAH",
            "bank_account_balance": 505.01,
            "bank_account_currency": "UAH",
            "bank_account_details": "*0000",
            "counterparty_details": None
        },
    ]
    
    for i, (example, expected) in enumerate(zip(examples, expected_results), 1):
        app_name = example.get('app_name', '')
        title = example.get('title', '')
        content = example.get('content', '')
        
        print(f"\nПример {i} ({app_name}):")
        print(f"  Входные данные:")
        print(f"    app_name: {app_name}")
        print(f"    title: {title}")
        print(f"    content: {content[:60]}...")
        
        result = parser.parse(content, app_name, title)
        
        # Check all 7 fields
        fields_to_check = [
            "operation_type",
            "operation_amount",
            "operation_currency",
            "bank_account_balance",
            "bank_account_currency",
            "bank_account_details",
            "counterparty_details"
        ]
        
        print(f"  Ожидаемый результат:")
        for field in fields_to_check:
            print(f"    {field}: {expected[field]}")
        
        print(f"  Полученный результат:")
        for field in fields_to_check:
            print(f"    {field}: {result[field]}")
        
        # Validate all fields
        for field in fields_to_check:
            expected_value = expected[field]
            actual_value = result[field]
            
            if expected_value is None:
                assert actual_value is None, \
                    f"Пример {i}: Поле {field} должно быть None, получено: {actual_value}"
            else:
                assert actual_value == expected_value, \
                    f"Пример {i}: Неверное значение поля {field}. Ожидалось: {expected_value}, получено: {actual_value}"
        
        print(f"  ✓ Пример {i} пройден (все 7 полей проверены)")


def parse_test_case_file(file_path: str) -> list:
    """
    Parse test_case.txt file that contains multiple examples separated by empty lines.
    
    Returns:
        List of dictionaries with app_name, title, and content for each example
    """
    examples = []
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    current_example = {}
    current_content_lines = []
    in_content = False
    
    for line in lines:
        stripped = line.strip()
        
        # Empty line indicates end of current example
        if not stripped:
            if current_example:
                if current_content_lines:
                    current_example['content'] = '\n'.join(current_content_lines)
                examples.append(current_example)
                current_example = {}
                current_content_lines = []
                in_content = False
            continue
        
        if stripped.startswith('app_name:'):
            if current_example:
                if current_content_lines:
                    current_example['content'] = '\n'.join(current_content_lines)
                examples.append(current_example)
                current_example = {}
                current_content_lines = []
            current_example['app_name'] = stripped.split('app_name:', 1)[1].strip()
            in_content = False
        elif stripped.startswith('title:'):
            current_example['title'] = stripped.split('title:', 1)[1].strip()
            in_content = False
        elif stripped.startswith('content:'):
            content_part = stripped.split('content:', 1)[1].strip()
            if content_part == '|':
                in_content = True
            else:
                current_content_lines.append(content_part)
                in_content = True
        elif in_content:
            current_content_lines.append(stripped)
        elif current_example:
            # If we have app_name/title but no content: yet, treat as content
            current_content_lines.append(stripped)
            in_content = True
    
    # Add last example if exists
    if current_example:
        if current_content_lines:
            current_example['content'] = '\n'.join(current_content_lines)
        examples.append(current_example)
    
    return examples


def main_cli():
    """Command-line interface for testing parser with custom arguments."""
    import sys
    import argparse
    import glob
    import os
    
    # Get directory where script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    test_case_path = os.path.join(script_dir, 'test_case.txt')
    
    parser_arg = argparse.ArgumentParser(description='Тестирование парсера банковских транзакций')
    parser_arg.add_argument('-f', '--file', action='store_true', 
                          help='Создавать JSON файлы с результатами')
    parser_arg.add_argument('-d', '--directory', action='store_true',
                          help='Парсить все .txt файлы в директории')
    parser_arg.add_argument('app_name', nargs='?', help='Название приложения банка')
    parser_arg.add_argument('title', nargs='?', help='Заголовок уведомления')
    parser_arg.add_argument('content', nargs='?', help='Содержимое уведомления')
    
    args = parser_arg.parse_args()
    save_files = args.file
    
    if args.directory:
        parser = BankTransactionParser()
        txt_files = glob.glob(os.path.join(script_dir, '*.txt'))
        other_txt_files = [f for f in txt_files if os.path.basename(f) != 'test_case.txt']
        
        if not other_txt_files:
            print("✗ Не найдено .txt файлов для парсинга (кроме test_case.txt)")
            return
        
        print("="*60)
        print("Парсинг всех .txt файлов в директории")
        print("="*60)
        
        for txt_file in sorted(other_txt_files):
            try:
                result = parser.parse_file(txt_file)
                output_file = os.path.join(script_dir, os.path.basename(txt_file).replace('.txt', '_result.json'))
                parser.save_result(result, output_file)
                
                print(f"\n✓ {os.path.basename(txt_file)}")
                print(json.dumps(result, indent=4, ensure_ascii=False))
                print(f"  → Сохранено в {output_file}")
            except Exception as e:
                print(f"\n✗ Ошибка при парсинге {os.path.basename(txt_file)}: {e}")
        return
    
    if args.app_name and args.title and args.content:
        parser = BankTransactionParser()
        app_name = args.app_name
        title = args.title
        content = args.content
        
        print("="*60)
        print("Тестирование парсера с пользовательскими данными")
        print("="*60)
        print(f"app_name: {app_name}")
        print(f"title: {title}")
        print(f"content: {content[:100]}..." if len(content) > 100 else f"content: {content}")
        print("="*60)
        
        result = parser.parse(content, app_name, title)
        print("\nРезультат парсинга:")
        print(json.dumps(result, indent=4, ensure_ascii=False))
        
        output_file = os.path.join(script_dir, 'test_result.json')
        parser.save_result(result, output_file)
        print(f"\n✓ Результат сохранен в {output_file}")
    else:
        parser = BankTransactionParser()
        
        if not os.path.exists(test_case_path):
            print(f"✗ Файл test_case.txt не найден в {script_dir}")
            return
        
        print("="*60)
        print("Парсинг 5 примеров из test_case.txt")
        if save_files:
            print("Режим сохранения файлов включен (-f)")
        print("="*60)
        
        try:
            examples = parse_test_case_file(test_case_path)
            for i, example in enumerate(examples, 1):
                result = parser.parse(
                    example.get('content', ''),
                    example.get('app_name', ''),
                    example.get('title', '')
                )
                
                print(f"\nПример {i}:")
                print(json.dumps(result, indent=4, ensure_ascii=False))
                
                if save_files:
                    output_file = os.path.join(script_dir, f'test_case_example_{i}_result.json')
                    parser.save_result(result, output_file)
                    print(f"  → Сохранено в {output_file}")
            
            print("\n" + "="*60)
            print("Все примеры успешно обработаны!")
            print("="*60)
            
            # Try to import and run pytest
            try:
                import pytest
                
                print("\nЗапуск полных тестов pytest...")
                print("="*60 + "\n")
                
                # Get script file path
                script_file = os.path.abspath(__file__)
                
                # Run pytest with no cache and verbose output
                # Use -p no:cacheprovider to disable cache creation
                exit_code = pytest.main([
                    script_file, 
                    '-v', 
                    '-s',
                    '-p', 'no:cacheprovider'
                ])
                
                print("\n" + "="*60)
                if exit_code == 0:
                    print("Все тесты pytest пройдены успешно! ✓")
                else:
                    print(f"Тесты завершены с кодом: {exit_code}")
                print("="*60)
            except ImportError:
                print("\nДля запуска полных тестов установите pytest:")
                print("  pip install pytest")
            except Exception as e:
                print(f"\nОшибка при запуске pytest: {e}")
                import traceback
                traceback.print_exc()
        except Exception as e:
            print(f"✗ Ошибка при парсинге test_case.txt: {e}")


if __name__ == '__main__':
    main_cli()

