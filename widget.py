from PyQt5 import QtCore, QtWidgets
from PyQt5.QtNetwork import QTcpSocket, QHostAddress, QTcpServer
from sim import Ui_Form
import struct
class Widget(QtWidgets.QWidget, Ui_Form):
    def __init__(self, parent=None):
        super(QtWidgets.QWidget, self).__init__(parent)
        self.setupUi(self)
        self.tcp_socket = QTcpSocket()
        self.tcp_socket.readyRead.connect(self.on_read)
        self.pushButton.clicked.connect(self.on_switch)
        self.pushButton_send.clicked.connect(self.on_send)
        self.pushButton_switch.clicked.connect(self.on_change)
        self.tcp_server = QTcpServer()
        self.tcp_server.listen(QHostAddress.Any, 504)
        self.tcp_server.newConnection.connect(self.on_connect)
        self.pushButton_clear.clicked.connect(self.on_clear)

    def on_clear(self):
        self.textEdit_info.clear()

    def on_connect(self):
        client_socket = self.tcp_server.nextPendingConnection()
        client_socket.readyRead.connect(self.on_server_read)
        client_socket.disconnected.connect(self.on_disconnect)
        client_address = client_socket.peerAddress().toString()
        client_port = client_socket.peerPort()
        self.textEdit_info.append("connect from {}:{}".format(client_address, client_port))

    def on_disconnect(self):
        client_socket = self.sender()
        client_socket.deleteLater()
        client_address = client_socket.peerAddress().toString()
        client_port = client_socket.peerPort()
        self.textEdit_info.append("disconnect from {}:{}".format(client_address, client_port))

    def on_server_read(self):
        out = QtCore.QByteArray()
        client_socket = self.sender()
        out.append(client_socket.read(2))
        out.append(2, b'\x00')
        out.append(struct.pack('>H', 0x0AA5))
        out.append(bytes([0xFF, 4, 0]))
        out.append(struct.pack('>H', 4))
        property = ''
        def process(out, table1, table2):
            property = ''
            for row in range(6):
                for col in range(table1.columnCount()):
                    item = table1.item(row, col)
                    property += item.text()
            property += '00'
            for row in range(6, table1.rowCount()):
                for col in range(table1.columnCount()):
                    item = table1.item(row, col)
                    property += format(int(item.text()), '02b')

            property = int(property[::-1], base=2)
            property = struct.pack('>H', property)
            out.append(property)

            for row in range(table2.rowCount()):
                for col in range(table2.columnCount()):
                    item = table2.item(row, col)
                    if (row + 1) % 3 == 0:
                        out.append(struct.pack('>I', int(item.text())))
                    else:
                        out.append(struct.pack('>H', int(item.text())))

        process(out, self.tableWidget_p11, self.tableWidget_p12);
        process(out, self.tableWidget_p21, self.tableWidget_p22);
        process(out, self.tableWidget_p31, self.tableWidget_p32);
        process(out, self.tableWidget_p41, self.tableWidget_p42);
        out.append(2584, b'\x00')
        client_socket = self.sender()
        self.textEdit_info.append(client_socket.readAll().data().hex().upper())
        client_socket.write(out)
    def on_change(self):
        cur_index = self.stackedWidget.currentIndex()
        if cur_index == 0:
            self.pushButton_switch.setText('port 504')
        else:
            self.pushButton_switch.setText('port 503')
        self.stackedWidget.setCurrentIndex(1 - cur_index)

    def on_switch(self):
        if self.pushButton.text() == 'connect':
            self.tcp_socket.connectToHost(self.lineEdit_ip.text(), int(self.lineEdit_port.text()))
            if not self.tcp_socket.waitForConnected(2500):
                msg = self.tcp_socket.errorString()
                QtWidgets.QMessageBox.critical(self, "Error", msg)
            else:
                self.pushButton.setText('disconnect')
        else:
            self.tcp_socket.disconnectFromHost()
            self.pushButton.setText('connect')

    def on_send(self):
        if self.tabWidget_func.currentIndex() == 0:
            self.opm_operate()
        else:
            self.status_operate()

    def opm_operate(self):
        out = QtCore.QByteArray()
        out.append(struct.pack('>H', self.spinBox_sn.value()))
        out.append(b'\x00\x00\x00\x06\x06\x10')
        out.append(struct.pack('>H', self.spinBox_st.value()))
        out.append(struct.pack('>H', self.spinBox_nr.value()))
        out.append(bytes(self.spinBox_nb.value()))
        out.append(3200, b'\x00')
        property = '000000000000' + self.spinBox_clear_text.text() + self.spinBox_display_mode.text() + format(self.spinBox_msg_priority.value(), '02b')
        property = int(property, base=2)
        property = struct.pack('>H', property)
        out.append(property)

        set_bit = lambda num, pos: num | (1 << pos)
        station_sign = 0
        for row in range(self.listWidget_station_sign.count()):
            item = self.listWidget_station_sign.item(row)
            if item.checkState() == QtCore.Qt.Checked:
                station_sign = set_bit(station_sign, row)
        out.append(struct.pack('>Q', station_sign))

        out.append(struct.pack('>H', self.spinBox_train_id.value()))

        play_region = 0
        for row in range(self.listWidget_play_region.count()):
            item = self.listWidget_play_region.item(row)
            if item.checkState() == QtCore.Qt.Checked:
                play_region = set_bit(play_region, row)
        out.append(struct.pack('>I', play_region))

        for row in range(self.tableWidget.rowCount()):
            for col in range(self.tableWidget.columnCount()):
                item = self.tableWidget.item(row, col)
                out.append(bytes(int(item.text())))

        content = QtCore.QByteArray(self.textEdit.toPlainText().encode('unicode_escape'))
        out.append(QtCore.QByteArray(2048, b'\x00').replace(0, content.size(), content))
        self.tcp_socket.write(out)

    def status_operate(self):
        out = QtCore.QByteArray()
        sn = struct.pack('>H', self.spinBox_sn.value())
        out.append(sn)
        out.append(b'\x00\x00\x00\x06\x06\x04')
        st = struct.pack('>H', self.spinBox_st.value())
        out.append(st)
        nr = struct.pack('>H', self.spinBox_nr.value())
        out.append(nr)
        self.tcp_socket.write(out)

    def on_read(self):
        self.textEdit_recv.setText(self.tcp_socket.readAll().data().hex().upper())