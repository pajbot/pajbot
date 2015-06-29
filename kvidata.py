import pymysql

class KVIData:
    def __init__(self, sqlconn):
        self.sqlconn = sqlconn

    def get_cursor(self):
        self.sqlconn.ping()
        return self.sqlconn.cursor()

    def get_dictcursor(self):
        self.sqlconn.ping()
        return self.sqlconn.cursor(pymysql.cursors.DictCursor)

    def get(self, id):
        return self.fetch(id)

    def fetch(self, id):
        cursor = self.get_cursor()

        cursor.execute('SELECT `value` FROM `tb_idata` WHERE `id`=%s', (id))
        row = cursor.fetchone()

        cursor.close()

        if row:
            return row[0]
        else:
            return 0

    def fetch_all(self, type):
        cursor = self.get_dictcursor()
        cursor.execute('SELECT `id` as `key`, `value` FROM `tb_idata` WHERE `type`=%s', (type))
        return cursor.fetchall()

    def inc(self, id):
        cursor = self.get_cursor()
        cursor.execute('UPDATE `tb_idata` SET `value`=`value`+1 WHERE `id`=%s', (id))
        cursor.close()

    def dec(self, id):
        cursor = self.get_cursor()
        cursor.execute('UPDATE `tb_idata` SET `value`=`value`-1 WHERE `id`=%s', (id))
        cursor.close()

    def set(self, id, value):
        cursor = self.get_cursor()
        cursor.execute('UPDATE `tb_idata` SET `value`=%s WHERE `id`=%s', (value, id))
        cursor.close()

    def insert(self, id, value, type='value'):
        cursor = self.get_cursor()
        cursor.execute('INSERT INTO `tb_idata` (`id`, `value`, `type`) VALUES(%s, %s, %s) ON DUPLICATE KEY UPDATE value=%s',
                (id, value, type, value))
        cursor.close()
