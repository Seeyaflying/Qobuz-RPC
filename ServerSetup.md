Part 1: Setting Up the Google Cloud ServerThis part is done on the Google Cloud website.1.Create a Google Cloud Account: If you don't have one, sign up for Google Cloud. New users get a significant free credit, which is more than enough for this project.2.Create a New Project: In the Google Cloud Console, create a new project (e.g., "qobuz-rpc-server").3.Create the Virtual Machine (VM) Instance:◦Navigate to Compute Engine > VM instances.◦Click "Create Instance".◦Name: Give it a simple name, like rpc-server-vm.◦Region and Zone: Choose a region close to you (e.g., us-central1). The zone doesn't matter as much (us-central1-a).◦Machine Configuration: This is the most important step for the free tier.▪Series: E2▪Machine type: e2-micro (This is part of the free tier).◦Boot Disk:▪Click "Change".▪Operating system: Debian▪Version: Debian GNU/Linux 11 (bullseye) or newer. This is a stable, lightweight choice.▪Click "Select".◦Firewall:▪Check the box for "Allow HTTP traffic".▪Check the box for "Allow HTTPS traffic".4.Create the Instance: Click the "Create" button at the bottom. Wait a minute or two for your new virtual server to be created. Once it's ready, you will see a green checkmark and an External IP address. Copy this IP address.5.Create a Firewall Rule for Port 5000:◦In the Google Cloud navigation menu, go to VPC network > Firewall.◦Click "Create Firewall Rule".◦Name: allow-port-5000.◦Targets: Select "All instances in the network".◦Source IPv4 ranges: 0.0.0.0/0 (This means "allow traffic from any IP address").◦Protocols and ports:▪Select "Specified protocols and ports".▪Check the "TCP" box and enter 5000 in the field next to it.◦Click "Create". This opens the necessary port so your Android app can reach the Python server.Part 2: Setting Up the Server SoftwareNow we'll connect to the server and install everything it needs.1.Connect via SSH: On the VM instances page, find your rpc-server-vm and click the "SSH" button. This will open a browser-based command line terminal connected directly to your server.2.Install Python and Dependencies: Run the following commands one by one in the SSH terminal.Kotlin# Update the server's package list
sudo apt-get update

# Install Python, pip (Python's package installer), and Git
sudo apt-get install python3 python3-pip git -y

# Install the Python libraries your script needs
pip3 install Flask pypresence requests packaging waitress3.Install Discord: The pypresence library needs the actual Discord client to be running to function. We will install the Discord client for Linux.Kotlin# Download the Discord .deb package
wget -O discord.deb "https://discordapp.com/api/download?platform=linux&format=deb"

# Install the package (it may show some dependency errors, which is normal)
sudo dpkg -i discord.deb

# Fix any broken dependencies from the previous step
sudo apt-get install -f -y4.Upload Your Python Script:◦The easiest way is to use git. Upload your server.py file to a private or public GitHub repository.◦In the SSH terminal, clone your repository: git clone https://github.com/your-username/your-repo-name.git◦Then navigate into the folder: cd your-repo-namePart 3: Running the Server 24/7If you just run python3 server.py, the script will stop the moment you close the SSH window. We need to run it as a persistent background service using systemd, which is the standard on modern Linux.1.Create a Service File: In your SSH terminal, create a new service file using the nano text editor.sudo nano /etc/systemd/system/rpc_server.service2.Paste the Service Configuration: Paste the following text into the nano editor. You must replace /home/your_user/your-repo-name with the actual path to your server.py file. (You can find your username by typing whoami in the terminal).Iniini
    [Unit]
    Description=Qobuz RPC Server
    After=network.target
    
    [Service]
    User=your_user 
    Group=your_user
    WorkingDirectory=/home/your_user/your-repo-name
    ExecStart=/usr/bin/python3 /home/your_user/your-repo-name/server.py
    Restart=always
    
    [Install]
    WantedBy=multi-user.targetbash # Reload systemd to recognize the new service file sudo systemctl daemon-reload# Start your service now
sudo systemctl start rpc_server

# Enable your service to start on boot
sudo systemctl enable rpc_server
```4.Check the Status: You can check if your server is running correctly with:Shell Scriptbash
    # Reload systemd to recognize the new service file
    sudo systemctl daemon-reload
    
    # Start your service now
    sudo systemctl start rpc_server
    
    # Enable your service to start on boot
    sudo systemctl enable rpc_serverkotlin // In ApiService.kt private const val BASE_URL = "http://34.123.45.67:5000/" // <-- Use your server's public IP ```3.Build and install the final APK on your phone.Your system is now complete. Your Android app will send song titles from anywhere in the world to your Google Cloud server, which is running your Python script 24/7, ready to update your Discord status. Congratulations on completing this complex and impressive project