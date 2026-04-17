import sys
sys.path.insert(0, '.')

from server import load_students, TEACHER_USER

# Test loading students
students = load_students()
print('Loaded students:')
for username, data in students.items():
    pwd = data.get('password')
    sid = data.get('id')
    print(f'  {username}: password={pwd}, id={sid}')

# Test login simulation
current_users = {}
current_users.update(TEACHER_USER)
current_users.update(students)

test_username = 'ganapathi'
test_password = '226m1a4224'

if test_username in current_users:
    user = current_users[test_username]
    print(f'\nTesting login for {test_username}:')
    stored_pwd = user.get('password')
    print(f'  Stored password: {stored_pwd}')
    print(f'  Provided password: {test_password}')
    match = stored_pwd == test_password
    print(f'  Match: {match}')
    if match:
        print('  ✅ Login would succeed!')
    else:
        print('  ❌ Login would fail!')
else:
    print(f'\n{test_username} not found in users!')
