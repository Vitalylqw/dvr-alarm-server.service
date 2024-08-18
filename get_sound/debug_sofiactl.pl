use strict;
use warnings;
use IO::Socket::INET;
use JSON;
use Digest::MD5 qw(md5);

# Настройки подключения
my $host = '192.168.1.41';
my $port = 34567;
my $user = 'admin';
my $pass = 'Lud2704asz';

# Подключение к серверу
my $socket = IO::Socket::INET->new(
    PeerAddr => $host,
    PeerPort => $port,
    Proto    => 'tcp',
    Timeout  => 30,
    Type     => SOCK_STREAM
) or die "Could not connect to $host:$port\n";

# Функция для создания хэша пароля
sub make_hash {
    my $password = shift;
    my $hash = '';

    my $msg_md5 = md5($password);

    for my $i (0..7) {
        my $n = (ord(substr($msg_md5, 2*$i, 1)) + ord(substr($msg_md5, 2*$i+1, 1))) % 0x3e;
        if ($n > 9) {
            if ($n > 35) {
                $n += 61;
            } else {
                $n += 55;
            }
        } else {
            $n += 0x30;
        }
        $hash .= chr($n);
    }
    return $hash;
}

# Отправка пакета
sub send_packet {
    my ($socket, $msgid, $params) = @_;
    my @pkt_prefix_1 = (0xff, 0x00, 0x00, 0x00);
    my $sid = 0;
    my $sequence = 0;
    my $pkt_type = $msgid;
    my $msgid_pack = pack('s', 0) . pack('s', $pkt_type);
    my $pkt_prefix_data = pack('C*', @pkt_prefix_1) . pack('i', $sid) . pack('i', $sequence) . $msgid_pack;
    my $pkt_params_data = '';

    if (defined $params) {
        $pkt_params_data = encode_json($params);
    }

    $pkt_params_data .= pack('C', 0x0a);
    my $pkt_data = $pkt_prefix_data . pack('i', length($pkt_params_data)) . $pkt_params_data;

    print "Sending packet (hex): ", unpack('H*', $pkt_data), "\n";  # Вывод отправляемого пакета для отладки
    print "Sending packet (raw): $pkt_data\n";
    $socket->send($pkt_data);
}

# Получение ответа
sub receive_response {
    my $socket = shift;
    my $header;
    $socket->recv($header, 24);
    print "Header received (hex): ", unpack('H*', $header), "\n";  # Вывод заголовка для отладки
    print "Header received (raw): $header\n";

    my ($version, $sid, $seq, $channel, $endflag, $msgid, $size) = unpack('a4i2C2i', $header);
    my $reply_head = {
        'Version' => $version,
        'SessionID' => $sid,
        'Sequence' => $seq,
        'MessageId' => $msgid,
        'Content_Length' => $size,
        'Channel' => $channel,
        'EndFlag' => $endflag
    };

    my $data;
    $socket->recv($data, $size);
    print "Received data (hex): ", unpack('H*', $data), "\n";  # Вывод полученных данных для отладки
    print "Received data (raw): $data\n";

    return ($reply_head, $data);
}

# Авторизация
sub login {
    my ($socket, $user, $pass) = @_;
    my $data = {
        'EncryptType' => 'MD5',
        'LoginType' => 'DVRIP-Web',
        'PassWord' => make_hash($pass),
        'UserName' => $user
    };
    print "Login data: " . encode_json($data) . "\n";  # Вывод данных авторизации для отладки
    send_packet($socket, 1000, $data);
    my ($reply_head, $data) = receive_response($socket);
    print "Response data: $data\n";  # Вывод данных ответа для отладки

    my $response = decode_json($data);
    die 'Authentication failed' if $response->{'Ret'} >= 200;
    return $response;
}

# Основная программа
my $response = login($socket, $user, $pass);
print "Login response: " . encode_json($response) . "\n";

$socket->close();
