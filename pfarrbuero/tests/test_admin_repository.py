import unittest
from admin_repository import AdminRepository

class AdminValidationTests(unittest.TestCase):
    def test_invalid_org_type_rejected_before_database(self):
        repo=AdminRepository.__new__(AdminRepository)
        with self.assertRaises(ValueError): repo.create_org_unit("unknown","x","X",None)
    def test_diocese_cannot_have_parent(self):
        repo=AdminRepository.__new__(AdminRepository)
        with self.assertRaises(ValueError): repo.create_org_unit("diocese","x","X","10000000-0000-0000-0000-000000000001")
    def test_non_root_unit_requires_parent(self):
        repo=AdminRepository.__new__(AdminRepository)
        with self.assertRaises(ValueError): repo.create_org_unit("parish","p1","Pfarrei",None)
    def test_invalid_user_email_rejected_before_database(self):
        repo=AdminRepository.__new__(AdminRepository)
        with self.assertRaises(ValueError): repo.create_user("not-an-email","Test")

if __name__=="__main__": unittest.main()
