import sqlite3
from datetime import datetime
from typing import List, Tuple, Optional, Any, Dict

class DatabaseManager:
    def __init__(self, db_name: str = 'chillman.db'):
        self.db_name = db_name
        
    def __enter__(self):
        self.conn = sqlite3.connect(self.db_name)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.commit()
        self.conn.close()

class UserManager:
    @staticmethod
    def verify_user(username: str, password: str) -> Tuple[bool, Optional[str]]:
        with DatabaseManager() as db:
            user = db.cursor.execute(
                'SELECT role FROM users WHERE username = ? AND password = ?',
                (username, password)
            ).fetchone()
            
            if user:
                return True, user['role']
            return False, None
    
    @staticmethod
    def create_user(username: str, password: str, role: str = 'Работник') -> bool:
        try:
            with DatabaseManager() as db:
                db.cursor.execute(
                    'INSERT INTO users (username, password, role) VALUES (?, ?, ?)',
                    (username, password, role)
                )
                return True
        except sqlite3.IntegrityError:
            return False
    
    @staticmethod
    def update_user_role(username: str, new_role: str) -> bool:
        with DatabaseManager() as db:
            db.cursor.execute(
                'UPDATE users SET role = ? WHERE username = ?',
                (new_role, username)
            )
            return db.cursor.rowcount > 0
    
    @staticmethod
    def delete_user(username: str) -> bool:
        with DatabaseManager() as db:
            db.cursor.execute('DELETE FROM users WHERE username = ?', (username,))
            return db.cursor.rowcount > 0
    
    @staticmethod
    def get_all_users() -> List[sqlite3.Row]:
        with DatabaseManager() as db:
            return db.cursor.execute('SELECT * FROM users').fetchall()

class ClientManager:
    @staticmethod
    def add_client(data: dict) -> bool:
        """
        Добавляет нового клиента в базу данных
        Args:
            data: словарь с данными клиента
        Returns:
            bool: True если успешно, False если произошла ошибка
        """
        try:
            with DatabaseManager() as db:
                # Разделяем данные на основную информацию и финансовую
                info_data = {
                    'last_name': data.get('last_name'),
                    'first_name': data.get('first_name'),
                    'middle_name': data.get('middle_name'),
                    'birth_date': data.get('birth_date'),
                    'phone': data.get('phone'),
                    'email': data.get('email'),
                    'address': data.get('address')
                }
                
                # Добавляем основную информацию
                fields = ', '.join(info_data.keys())
                placeholders = ', '.join(['?' for _ in info_data])
                values = tuple(info_data.values())
                
                query = f"INSERT INTO client_info ({fields}) VALUES ({placeholders})"
                db.cursor.execute(query, values)
                client_id = db.cursor.lastrowid
                
                # Добавляем финансовую информацию
                db.cursor.execute('''
                    INSERT INTO client_financial (client_id, tariff, balance)
                    VALUES (?, ?, ?)
                ''', (client_id, data.get('tariff', 'Стандарт'), data.get('balance', 0.00)))
                
                return True
        except sqlite3.Error as e:
            print(f"Ошибка при добавлении клиента: {e}")
            return False
            
    @staticmethod
    def update_client(data: Dict[str, Any]) -> bool:
        """Обновление данных клиента"""
        try:
            with DatabaseManager() as db:
                # Обновляем основную информацию
                db.cursor.execute('''
                    UPDATE client_info SET
                        last_name = ?,
                        first_name = ?,
                        middle_name = ?,
                        birth_date = ?,
                        phone = ?,
                        email = ?,
                        address = ?,
                        updated_at = datetime('now', 'localtime')
                    WHERE id = ?
                ''', (
                    data.get('last_name'),
                    data.get('first_name'),
                    data.get('middle_name'),
                    data.get('birth_date'),
                    data.get('phone'),
                    data.get('email'),
                    data.get('address'),
                    data.get('id')
                ))
                
                # Обновляем финансовую информацию
                db.cursor.execute('''
                    UPDATE client_financial SET
                        tariff = ?,
                        balance = ?,
                        updated_at = datetime('now', 'localtime')
                    WHERE client_id = ?
                ''', (
                    data.get('tariff'),
                    data.get('balance'),
                    data.get('id')
                ))
                return True
        except Exception as e:
            print(f"Error updating client: {e}")
            return False
            
    @staticmethod
    def get_all_clients() -> List[Dict[str, Any]]:
        """Получение списка всех клиентов"""
        try:
            with DatabaseManager() as db:
                db.cursor.execute('''
                    SELECT 
                        ci.id, ci.last_name, ci.first_name, ci.middle_name, ci.birth_date,
                        ci.phone, ci.email, ci.address, cf.tariff, cf.balance,
                        ci.last_call, ci.last_caller, ci.last_offer,
                        ci.created_at, ci.updated_at
                    FROM client_info ci
                    LEFT JOIN client_financial cf ON ci.id = cf.client_id
                    ORDER BY ci.last_name, ci.first_name
                ''')
                
                columns = ['id', 'last_name', 'first_name', 'middle_name', 'birth_date',
                          'phone', 'email', 'address', 'tariff', 'balance',
                          'last_call', 'last_caller', 'last_offer',
                          'created_at', 'updated_at']
                          
                return [dict(zip(columns, row)) for row in db.cursor.fetchall()]
                
        except sqlite3.Error as e:
            print(f"Ошибка при получении списка клиентов: {e}")
            return []
        
    @staticmethod
    def get_client_by_id(client_id: int) -> Optional[Dict[str, Any]]:
        """Получение данных клиента по ID"""
        try:
            with DatabaseManager() as db:
                db.cursor.execute('''
                    SELECT 
                        ci.id, ci.last_name, ci.first_name, ci.middle_name, ci.birth_date,
                        ci.phone, ci.email, ci.address, cf.tariff, cf.balance,
                        ci.last_call, ci.last_caller, ci.last_offer,
                        ci.created_at, ci.updated_at
                    FROM client_info ci
                    LEFT JOIN client_financial cf ON ci.id = cf.client_id
                    WHERE ci.id = ?
                ''', (client_id,))
                
                row = db.cursor.fetchone()
                if row:
                    columns = ['id', 'last_name', 'first_name', 'middle_name', 'birth_date',
                              'phone', 'email', 'address', 'tariff', 'balance',
                              'last_call', 'last_caller', 'last_offer',
                              'created_at', 'updated_at']
                    return dict(zip(columns, row))
                return None
                
        except sqlite3.Error as e:
            print(f"Ошибка при получении данных клиента: {e}")
            return None

    @staticmethod
    def delete_client(client_id: int) -> bool:
        """Удаляет клиента из базы данных"""
        try:
            with DatabaseManager() as db:
                # Благодаря ON DELETE CASCADE в client_financial,
                # удаление записи из client_info автоматически удалит
                # соответствующую запись из client_financial
                db.cursor.execute("DELETE FROM client_info WHERE id = ?", (client_id,))
                return True
        except sqlite3.Error as e:
            print(f"Ошибка при удалении клиента: {e}")
            return False

    @staticmethod
    def search_clients(query: str) -> List[Dict[str, Any]]:
        """
        Поиск клиентов по заданному запросу
        Args:
            query: строка поиска
        Returns:
            List[Dict]: список клиентов, соответствующих запросу
        """
        try:
            with DatabaseManager() as db:
                search_pattern = f"%{query}%"
                db.cursor.execute('''
                    SELECT 
                        ci.id, ci.last_name, ci.first_name, ci.middle_name, ci.birth_date,
                        ci.phone, ci.email, ci.address, cf.tariff, cf.balance,
                        ci.last_call, ci.last_caller, ci.last_offer,
                        ci.created_at, ci.updated_at
                    FROM client_info ci
                    LEFT JOIN client_financial cf ON ci.id = cf.client_id
                    WHERE 
                        ci.last_name LIKE ? OR
                        ci.first_name LIKE ? OR
                        ci.middle_name LIKE ? OR
                        ci.phone LIKE ? OR
                        ci.email LIKE ? OR
                        ci.address LIKE ? OR
                        cf.tariff LIKE ?
                    ORDER BY ci.last_name, ci.first_name
                ''', (search_pattern,) * 7)
                
                columns = ['id', 'last_name', 'first_name', 'middle_name', 'birth_date',
                          'phone', 'email', 'address', 'tariff', 'balance',
                          'last_call', 'last_caller', 'last_offer',
                          'created_at', 'updated_at']
                
                return [dict(zip(columns, row)) for row in db.cursor.fetchall()]
                
        except sqlite3.Error as e:
            print(f"Ошибка при поиске клиентов: {e}")
            return []

    @staticmethod
    def update_last_call(client_id: int, username: str) -> bool:
        """Обновляет информацию о последнем звонке клиенту"""
        try:
            current_time = datetime.now().strftime('%d.%m.%Y %H:%M:%S')
            with DatabaseManager() as db:
                db.cursor.execute('''
                    UPDATE client_info 
                    SET last_call = ?, last_caller = ?
                    WHERE id = ?
                ''', (current_time, username, client_id))
                db.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Ошибка при обновлении информации о звонке: {e}")
            return False
