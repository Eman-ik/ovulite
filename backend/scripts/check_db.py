#!/usr/bin/env python
import psycopg2

try:
    conn = psycopg2.connect('postgresql://ovulite:ovulite_dev_password@localhost:5432/ovulite')
    cursor = conn.cursor()

    print('Current Users in Database')
    print('='*60)

    cursor.execute('SELECT user_id, username, email, role, active FROM users ORDER BY user_id')
    result = cursor.fetchall()

    if not result:
        print('No users found!')
    else:
        for uid, username, email, role, active in result:
            status = 'ACTIVE' if active else 'inactive'
            print(f'{uid}. {username:15} | {role:15} | {status:8}')
            
    cursor.close()
    conn.close()
    print('\n✓ Database check complete')
except Exception as e:
    print(f'Error: {e}')
