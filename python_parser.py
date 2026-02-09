import re
import json
from typing import Dict, Optional, Any


class BankTransactionParser:
    """Universal parser for bank transaction notifications in various formats."""
    
    def __init__(self):
        # Currency patterns
        self.currency_pattern = r'(UAH|USD|EUR|GBP|PLN)'
        
        # Amount patterns - handles both comma and dot as decimal separator, and spaces (e.g., "1 250.50" or "3 500,00")
        # Pattern matches: "1 250.50", "3 500.00", "1250.50", "1250,50", etc.
        self.amount_pattern = r'(\d+(?:\s+\d+)*(?:[.,]\d+)?|\d+)'
    
    def _normalize_number(self, number_str: str) -> float:
        """Normalize number string (replace comma with dot, remove spaces) and convert to float."""
        # Remove spaces and replace comma with dot
        normalized = number_str.replace(' ', '').replace(',', '.')
        return float(normalized)
        
    def parse(self, text_content: str, app_name: str = "", title: str = "") -> Dict[str, Any]:
        """
        Parse bank transaction text and extract structured data.
        
        Args:
            text_content: The main content text to parse
            app_name: Optional app name (e.g., "UKRSIB", "PUMB")
            title: Optional title field
            
        Returns:
            Dictionary with parsed transaction data
        """
        # Keep original content for line-based parsing, but normalize for number matching
        # We'll normalize commas to dots only when matching numbers
        original_content = text_content
        original_title = title if title else ""
        
        # Initialize result
        result = {
            "bank_account_balance": None,
            "bank_account_currency": None,
            "bank_account_details": None,
            "operation_amount": None,
            "operation_currency": None,
            "operation_type": None,
            "counterparty_details": None
        }
        
        # Determine operation type and parse accordingly
        content_lower = original_content.lower()
        title_lower = original_title.lower()
        
        # Check for balance info only (no transaction)
        if self._is_balance_info_only(original_content, original_title):
            return self._parse_balance_info(original_content, original_title, result)
        
        # Check for incoming transaction
        if self._is_incoming(original_content, original_title):
            return self._parse_incoming(original_content, original_title, result)
        
        # Check for blocking
        if self._is_blocking(original_content):
            return self._parse_blocking(original_content, result)
        
        # Check for outgoing transaction
        if self._is_outgoing(original_content, original_title):
            return self._parse_outgoing(original_content, original_title, result)
        
        # Default: try to extract what we can
        return self._parse_generic(original_content, original_title, result)
    
    def _is_balance_info_only(self, content: str, title: str) -> bool:
        """Check if this is just a balance inquiry without a transaction."""
        content_lower = content.lower()
        title_lower = title.lower()
        
        # CA+ format: "Баланс:" without operation indicators
        if 'баланс:' in content_lower and 'переказ' not in content_lower:
            return True
        
        # Check if there's no operation amount mentioned
        operation_keywords = [
            'переказ', 'perekaz', 'transfer',
            'blokuvannia', 'блокування', 'blocking',
            'сума', 'suma', 'amount', 'сумма',
            'надходження', 'incoming',
            'зняття', 'снятие', 'withdrawal',
            'платіж', 'платеж', 'payment'
        ]
        if 'баланс' in content_lower and not any(keyword in content_lower for keyword in operation_keywords):
            return True
        
        return False
    
    def _is_incoming(self, content: str, title: str) -> bool:
        """Check if this is an incoming transaction."""
        content_lower = content.lower()
        title_lower = title.lower()
        
        incoming_keywords = [
            'perekaz:',  # UKRSIB incoming
            'perekaz',  # UKRSIB incoming (without colon)
            'надходження',  # PUMB incoming
            'поступление',  # Russian incoming
            'incoming',  # English
            'пополнение',  # Top-up
            'поповнення',  # Top-up (Ukrainian)
            'replenishment',  # Top-up
            'deposit',  # Deposit
            'депозит',  # Deposit
        ]
        
        return any(keyword in content_lower or keyword in title_lower for keyword in incoming_keywords)
    
    def _is_blocking(self, content: str) -> bool:
        """Check if this is a blocking/reject operation."""
        blocking_keywords = [
            'blokuvannia:',
            'blokuvannya',
            'блокування',
            'блокировка',
            'блокирование',
            'blocking',
            'block',
            'reject',
            'відхилення',
            'отклонение'
        ]
        content_lower = content.lower()
        return any(keyword in content_lower for keyword in blocking_keywords)
    
    def _is_outgoing(self, content: str, title: str) -> bool:
        """Check if this is an outgoing transaction."""
        content_lower = content.lower()
        title_lower = title.lower()
        
        # Negative amount in title indicates outgoing
        if re.search(r'-\s*\d+', title_lower):
            return True
        
        # Outgoing keywords
        outgoing_keywords = [
            'переказ з картки на картку',
            'переказ з карты на карту',
            'transfer from card to card',
            'зняття',
            'снятие',
            'withdrawal',
            'виведення',
            'вывод',
            'outgoing',
            'out',
            'списання',
            'списание',
            'debit',
            'платіж',
            'платеж',
            'payment',
            'оплата',
            'оплата'
        ]
        return any(keyword in content_lower or keyword in title_lower for keyword in outgoing_keywords)
    
    def _parse_balance_info(self, content: str, title: str, result: Dict) -> Dict:
        """Parse balance information only (no transaction)."""
        result["operation_type"] = "balance_info"
        result["operation_amount"] = None
        result["operation_currency"] = None
        result["counterparty_details"] = None
        
        # Extract balance: "Баланс: 5853,79 UAH" or "Баланс: 5853.79 UAH"
        # Handle both comma/dot and spaces in amount
        balance_match = re.search(r'баланс:\s*' + self.amount_pattern + r'\s*' + self.currency_pattern, content, re.IGNORECASE)
        if balance_match:
            result["bank_account_balance"] = self._normalize_number(balance_match.group(1))
            result["bank_account_currency"] = balance_match.group(2)
        
        # Extract card details
        card_match = re.search(r'картка:\s*([*0-9]+)', content, re.IGNORECASE)
        if card_match:
            result["bank_account_details"] = card_match.group(1)
        
        return result
    
    def _parse_incoming(self, content: str, title: str, result: Dict) -> Dict:
        """Parse incoming transaction."""
        result["operation_type"] = "in"
        
        # UKRSIB format: "Perekaz: CLIENT001 ... na kartku 000000****0000 na sumu 1000.00UAH. Dostupno 1154.16UAH."
        if 'perekaz:' in content.lower():
            # Extract counterparty (after "Perekaz:" and before date, or at the end if no date pattern)
            # First try to get counterparty before date - this is the primary counterparty
            counterparty_match = re.search(r'perekaz:\s*([A-Z0-9]+)', content, re.IGNORECASE)
            primary_counterparty = None
            if counterparty_match:
                primary_counterparty = counterparty_match.group(1)
                result["counterparty_details"] = primary_counterparty
            
            # Check if there's a counterparty at the end (after "Dostupno" section)
            # Pattern: "Dostupno 5 000.00USD. PAYPAL*TRANSFER" or "Dostupno 1154.16UAH. EXAMPLE.COM"
            # Only use end counterparty if we don't have a primary one, or if it's a special case like PAYPAL
            if not primary_counterparty:
                dostupno_match = re.search(r'dostupno\s+' + self.amount_pattern + r'\s*' + self.currency_pattern + r'\.\s+', content, re.IGNORECASE)
                if dostupno_match:
                    after_dostupno = content[dostupno_match.end():].strip()
                    # Extract counterparty (everything until period or end)
                    counterparty_match = re.match(r'^([A-Z][A-Z0-9\s*\-\.]+?)(?:\.|$)', after_dostupno, re.IGNORECASE)
                    if counterparty_match:
                        end_counterparty = counterparty_match.group(1).strip()
                        # Only use end counterparty if it's meaningful (not EXAMPLE.COM, and longer than 2 chars)
                        if len(end_counterparty) > 2 and end_counterparty.upper() not in ['EXAMPLE.COM', 'EXAMPLE']:
                            result["counterparty_details"] = end_counterparty
            
            # Extract operation amount: "na sumu 1 250.50USD" or "na sumu 1000.00UAH"
            # Handle both attached and separated currency
            amount_match = re.search(r'na sumu\s+' + self.amount_pattern + r'\s*' + self.currency_pattern, content, re.IGNORECASE)
            if amount_match:
                result["operation_amount"] = self._normalize_number(amount_match.group(1))
                result["operation_currency"] = amount_match.group(2)
            
            # Extract balance: "Dostupno 5 000.00USD" or "Dostupno 1154.16UAH"
            # Handle both attached and separated currency
            balance_match = re.search(r'dostupno\s+' + self.amount_pattern + r'\s*' + self.currency_pattern, content, re.IGNORECASE)
            if balance_match:
                result["bank_account_balance"] = self._normalize_number(balance_match.group(1))
                result["bank_account_currency"] = balance_match.group(2)
            
            # Extract card: "na kartku 000000****0000"
            card_match = re.search(r'na kartku\s+([*0-9]+)', content, re.IGNORECASE)
            if card_match:
                result["bank_account_details"] = card_match.group(1)
        
        # PUMB format: "2000.0UAH\nCLIENT NAME\n...\nКартка: *0000\nДоступно: 2000.0UAH"
        # Or: "3 500.00 UAH\nCOMPANY XYZ LTD.\n...\nДоступно: 10 250.00 UAH"
        # Or: "Надходження: 200.0UAH" (single line format)
        elif 'надходження' in title.lower() or 'доступно:' in content.lower() or 'надходження:' in content.lower():
            amount_match = None
            
            # Check for "Надходження: 200.0UAH" format first
            if 'надходження:' in content.lower():
                amount_match = re.search(r'надходження:\s*' + self.amount_pattern + r'\s*' + self.currency_pattern, content, re.IGNORECASE)
            
            # Extract operation amount from first line or content
            # Handle both attached and separated currency: "2000.0UAH" or "3 500.00 UAH"
            if not amount_match:
                amount_match = re.search(r'^' + self.amount_pattern + r'\s*' + self.currency_pattern, content, re.IGNORECASE)
            if not amount_match:
                # Try to find amount before currency anywhere (but not in "Доступно:")
                for match in re.finditer(self.amount_pattern + r'\s*' + self.currency_pattern, content, re.IGNORECASE):
                    # Check if it's not part of "Доступно:"
                    start_pos = match.start()
                    context_before = content[max(0, start_pos-20):start_pos].lower()
                    if 'доступно' not in context_before:
                        amount_match = match
                        break
            
            if amount_match:
                result["operation_amount"] = self._normalize_number(amount_match.group(1))
                result["operation_currency"] = amount_match.group(2)
            
            # Extract balance: "Доступно: 2000.0UAH" or "Доступно: 10 250.00 UAH"
            # Handle both attached and separated currency
            balance_match = re.search(r'доступно:\s*' + self.amount_pattern + r'\s*' + self.currency_pattern, content, re.IGNORECASE)
            if balance_match:
                result["bank_account_balance"] = self._normalize_number(balance_match.group(1))
                result["bank_account_currency"] = balance_match.group(2)
            
            # Extract card: "Картка: *0000"
            card_match = re.search(r'картка:\s*([*0-9]+)', content, re.IGNORECASE)
            if card_match:
                result["bank_account_details"] = card_match.group(1)
            
            # Extract counterparty - usually on a separate line after the amount
            lines = content.split('\n') if '\n' in content else [content]
            for i, line in enumerate(lines):
                line_stripped = line.strip()
                # Check if this line has amount+currency (operation amount)
                if re.search(r'^' + self.amount_pattern + r'(' + self.currency_pattern + r')', line_stripped, re.IGNORECASE):
                    # Next non-empty line that's not a date, not "Картка:", not "Доступно:" is likely counterparty
                    for j in range(i + 1, min(i + 4, len(lines))):
                        next_line = lines[j].strip()
                        if not next_line:
                            continue
                        # Skip if it's a date pattern, card info, or balance info
                        if (re.match(r'^\d+[-.]\d+[-.]\d+', next_line) or
                            'картка:' in next_line.lower() or
                            'доступно:' in next_line.lower() or
                            re.search(r'^\d+\.\d+', next_line)):
                            continue
                        # This should be the counterparty
                        if len(next_line) > 2:
                            result["counterparty_details"] = next_line
                            break
                    break
        
        return result
    
    def _parse_blocking(self, content: str, result: Dict) -> Dict:
        """Parse blocking/reject operation."""
        result["operation_type"] = "reject"
        
        # Extract amount - try multiple patterns
        amount_match = None
        
        # Pattern 1: "Suma 2540.43UAH" or "Suma 1 250.50USD" (UKRSIB)
        # Handle both attached and separated currency
        amount_match = re.search(r'(?:suma|сума|amount|сумма)\s+' + self.amount_pattern + r'\s*' + self.currency_pattern, content, re.IGNORECASE)
        
        # Pattern 2: Just amount before currency
        if not amount_match:
            # Find amount that's not the balance
            all_amounts = list(re.finditer(self.amount_pattern + r'\s*' + self.currency_pattern, content, re.IGNORECASE))
            if len(all_amounts) >= 2:
                # Usually first is operation, last is balance
                amount_match = all_amounts[0]
        
        if amount_match:
            result["operation_amount"] = self._normalize_number(amount_match.group(1))
            result["operation_currency"] = amount_match.group(2)
        
        # Extract balance - try multiple patterns
        balance_match = None
        
        # Pattern 1: "Dostupno 78126.18UAH" or "Dostupno 5 000.00USD" (UKRSIB)
        # Handle both attached and separated currency
        balance_match = re.search(r'(?:dostupno|доступно|available)\s+' + self.amount_pattern + r'\s*' + self.currency_pattern, content, re.IGNORECASE)
        
        # Pattern 2: "Баланс: 5853.79 UAH"
        if not balance_match:
            balance_match = re.search(r'(?:баланс|balance):\s*' + self.amount_pattern + r'\s*' + self.currency_pattern, content, re.IGNORECASE)
        
        if balance_match:
            result["bank_account_balance"] = self._normalize_number(balance_match.group(1))
            result["bank_account_currency"] = balance_match.group(2)
        
        # Extract card - try multiple patterns
        card_match = None
        
        # Pattern 1: "Kartka 000000****0000" (UKRSIB)
        card_match = re.search(r'(?:kartka|картка|card|карта)\s*:?\s*([*0-9]+)', content, re.IGNORECASE)
        
        # Pattern 2: Card number pattern anywhere
        if not card_match:
            card_match = re.search(r'([*0-9]{4,})', content)
        
        if card_match:
            result["bank_account_details"] = card_match.group(1)
        
        # Extract counterparty - try multiple patterns
        # Pattern 1: "Blokuvannia: ORDER001 PAYMENT*MERCHANT"
        counterparty_match = re.search(r'(?:blokuvannia|блокування|blocking|reject):\s*([A-Z0-9\s*\-]+?)(?:\s+\d+\.\d+\.\d+|\s+(?:kartka|картка|card))', content, re.IGNORECASE)
        
        if counterparty_match:
            counterparty = counterparty_match.group(1).strip()
            result["counterparty_details"] = counterparty
        else:
            # Try to find counterparty after operation type keyword
            for keyword in ['blokuvannia', 'блокування', 'blocking', 'reject']:
                if keyword in content.lower():
                    # Extract text after keyword until date or card
                    pattern = rf'{keyword}:\s*([^0-9]+?)(?:\s+\d+\.\d+\.\d+|\s+(?:kartka|картка|card)|$)'
                    match = re.search(pattern, content, re.IGNORECASE)
                    if match:
                        counterparty = match.group(1).strip()
                        if len(counterparty) > 2:
                            result["counterparty_details"] = counterparty
                            break
        
        return result
    
    def _parse_outgoing(self, content: str, title: str, result: Dict) -> Dict:
        """Parse outgoing transaction."""
        result["operation_type"] = "out"
        
        # TAS2U format: Title has "-1 000.00 UAH доступно 505.01 UAH *0000"
        # Handle spaces in amount: "1 000.00"
        if re.search(r'-\s*\d+', title):
            # Extract operation amount from title (negative, but store as positive)
            # Pattern: "-1 000.00 UAH" or "-1000.00 UAH"
            amount_match = re.search(r'-\s*' + self.amount_pattern + r'\s*' + self.currency_pattern, title, re.IGNORECASE)
            if amount_match:
                result["operation_amount"] = self._normalize_number(amount_match.group(1))
                result["operation_currency"] = amount_match.group(2)
            
            # Extract balance: "доступно 505.01 UAH"
            balance_match = re.search(r'(?:доступно|available)\s+' + self.amount_pattern + r'\s*' + self.currency_pattern, title, re.IGNORECASE)
            if balance_match:
                result["bank_account_balance"] = self._normalize_number(balance_match.group(1))
                result["bank_account_currency"] = balance_match.group(2)
            
            # Extract card: "*0000" at the end
            card_match = re.search(r'([*0-9]+)\s*$', title)
            if card_match:
                result["bank_account_details"] = card_match.group(1)
        else:
            # Try to extract from content
            # Extract operation amount
            amount_match = re.search(self.amount_pattern + r'\s*' + self.currency_pattern, content, re.IGNORECASE)
            if amount_match:
                result["operation_amount"] = self._normalize_number(amount_match.group(1))
                result["operation_currency"] = amount_match.group(2)
            
            # Extract balance
            balance_match = re.search(r'(?:доступно|available|баланс|balance)\s+' + self.amount_pattern + r'\s*' + self.currency_pattern, content, re.IGNORECASE)
            if balance_match:
                result["bank_account_balance"] = self._normalize_number(balance_match.group(1))
                result["bank_account_currency"] = balance_match.group(2)
            
            # Extract card
            card_match = re.search(r'(?:картка|card|карта)\s*:?\s*([*0-9]+)', content, re.IGNORECASE)
            if not card_match:
                card_match = re.search(r'([*0-9]{4,})', content)
            if card_match:
                result["bank_account_details"] = card_match.group(1)
        
        # Counterparty might be in content, but TAS2U example doesn't have explicit counterparty
        result["counterparty_details"] = None
        
        return result
    
    def _parse_generic(self, content: str, title: str, result: Dict) -> Dict:
        """Generic parsing fallback - extract what we can."""
        # Try to extract amounts and currencies
        # Handle both attached and separated currency
        amount_matches = list(re.finditer(self.amount_pattern + r'\s*' + self.currency_pattern, content, re.IGNORECASE))
        if amount_matches:
            # Use first match as operation amount
            match = amount_matches[0]
            result["operation_amount"] = self._normalize_number(match.group(1))
            result["operation_currency"] = match.group(2)
            
            # Use last match as balance if multiple
            if len(amount_matches) > 1:
                match = amount_matches[-1]
                result["bank_account_balance"] = self._normalize_number(match.group(1))
                result["bank_account_currency"] = match.group(2)
        
        # Try to extract card
        card_match = re.search(r'([*0-9]{4,})', content)
        if card_match:
            result["bank_account_details"] = card_match.group(1)
        
        return result
    
    def parse_file(self, file_path: str) -> Dict[str, Any]:
        """
        Parse a text file containing bank transaction data.
        
        Args:
            file_path: Path to the text file
            
        Returns:
            Dictionary with parsed transaction data
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        app_name = ""
        title = ""
        content_lines = []
        in_content = False
        
        for line in lines:
            stripped = line.strip()
            if not stripped:
                if in_content:
                    content_lines.append('')
                continue
            
            if stripped.startswith('app_name:'):
                app_name = stripped.split('app_name:', 1)[1].strip()
                in_content = False
            elif stripped.startswith('title:'):
                title = stripped.split('title:', 1)[1].strip()
                in_content = False
            elif stripped.startswith('content:'):
                content_part = stripped.split('content:', 1)[1].strip()
                # Handle YAML-style pipe: "content: |"
                if content_part == '|':
                    in_content = True
                    # Don't add the pipe itself, just mark that we're in content
                else:
                    content_lines.append(content_part)
                    in_content = True
            elif in_content:
                # Remove leading indentation (common in YAML-style multiline)
                content_lines.append(stripped)
            else:
                # If we haven't seen any prefix yet, treat as content
                content_lines.append(stripped)
                in_content = True
        
        content = '\n'.join(content_lines)
        return self.parse(content, app_name, title)


    def save_result(self, result: Dict[str, Any], output_path: str):
        """
        Save parsed result to a JSON file.
        
        Args:
            result: Parsed transaction data dictionary
            output_path: Path to save the JSON file
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=4, ensure_ascii=False)


def main():
    """Main function with multiple usage modes."""
    import sys
    import glob
    import os
    
    # Get directory where script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    test_case_path = os.path.join(script_dir, 'test_case.txt')
    
    parser = BankTransactionParser()
    
    # Check if command-line arguments are provided
    if len(sys.argv) >= 4:
        # Mode 1: Parse from command-line arguments
        # Usage: python python_parser.py "app_name" "title" "content"
        app_name = sys.argv[1]
        title = sys.argv[2]
        content = sys.argv[3]
        
        print("="*60)
        print("Парсинг из аргументов командной строки")
        print("="*60)
        print(f"app_name: {app_name}")
        print(f"title: {title}")
        print(f"content: {content[:100]}..." if len(content) > 100 else f"content: {content}")
        print("="*60)
        
        result = parser.parse(content, app_name, title)
        print("\nРезультат:")
        print(json.dumps(result, indent=4, ensure_ascii=False))
        
        # Save to file in script directory
        output_file = os.path.join(script_dir, 'result_from_args.json')
        parser.save_result(result, output_file)
        print(f"\n✓ Результат сохранен в {output_file}")
        return
    
    # Mode 2: Parse all .txt files in script directory
    txt_files = glob.glob(os.path.join(script_dir, '*.txt'))
    # Get just filenames for display
    txt_file_names = [os.path.basename(f) for f in txt_files]
    # Exclude test_case.txt from automatic parsing if other files exist
    other_txt_files = [(f, os.path.basename(f)) for f in txt_files if os.path.basename(f) != 'test_case.txt']
    
    if other_txt_files:
        # Parse other .txt files
        print("="*60)
        print("Парсинг всех .txt файлов в директории")
        print("="*60)
        
        for txt_file_path, txt_file_name in sorted(other_txt_files, key=lambda x: x[1]):
            try:
                result = parser.parse_file(txt_file_path)
                output_file = os.path.join(script_dir, txt_file_name.replace('.txt', '_result.json'))
                parser.save_result(result, output_file)
                
                print(f"\n✓ {txt_file_name}")
                print(json.dumps(result, indent=4, ensure_ascii=False))
                print(f"  → Сохранено в {output_file}")
            except Exception as e:
                print(f"\n✗ Ошибка при парсинге {txt_file_name}: {e}")
    else:
        # Mode 3: No other .txt files found, parse test_case.txt as default
        if os.path.exists(test_case_path):
            print("="*60)
            print("Парсинг test_case.txt (по умолчанию)")
            print("="*60)
            try:
                result = parser.parse_file(test_case_path)
                output_file = os.path.join(script_dir, 'test_case_result.json')
                parser.save_result(result, output_file)
                
                print(f"\n✓ test_case.txt")
                print(json.dumps(result, indent=4, ensure_ascii=False))
                print(f"  → Сохранено в {output_file}")
            except Exception as e:
                print(f"✗ Ошибка при парсинге test_case.txt: {e}")
        else:
            print(f"✗ Не найдено файлов .txt для парсинга в {script_dir}")


if __name__ == '__main__':
    main()

