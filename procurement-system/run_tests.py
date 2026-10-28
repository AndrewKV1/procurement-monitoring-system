import subprocess
import sys
import time

def run_tests():
    print("Запуск тестів системи закупівель")
    print("=" * 50)
    
    test_commands = [
        ["pytest", "test_procurement.py::TestDatabaseStructure", "-v"],
        ["pytest", "test_procurement.py::TestPurchaseRequests", "-v"],
        ["pytest", "test_procurement.py::TestUserFunctionality", "-v"],
        ["pytest", "test_procurement.py::TestSupplierFunctionality", "-v"],
        ["pytest", "test_procurement.py::TestAnalyticsFunctionality", "-v"]
    ]
    
    passed_tests = 0
    failed_tests = 0
    
    for cmd in test_commands:
        print(f"\nЗапуск: {' '.join(cmd)}")
        print("-" * 40)
        
        try:
            start_time = time.time()
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            elapsed_time = time.time() - start_time
            
            print(result.stdout)
            
            if result.returncode == 0:
                print(f"Тест пройдено ({elapsed_time:.2f}с)")
                passed_tests += 1
            else:
                print(f"Тест не пройдено ({elapsed_time:.2f}с)")
                failed_tests += 1
                
        except subprocess.TimeoutExpired:
            print("Перевищено час очікування")
            failed_tests += 1
        except Exception as e:
            print(f"Помилка: {e}")
            failed_tests += 1
    
    print("\n" + "=" * 50)
    print("Кінцеві результати:")
    print(f"Пройдено: {passed_tests}")
    print(f"Не пройдено: {failed_tests}")
    print(f"Успішність: {(passed_tests/(passed_tests+failed_tests))*100:.1f}%")
    
    if failed_tests == 0:
        print("\n Всі тести успішно пройдені!")
    else:
        print(f"\n  Знайдено {failed_tests} помилок, що потребують виправлення")
    
    return 0 if failed_tests == 0 else 1

if __name__ == "__main__":
    sys.exit(run_tests())