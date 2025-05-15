using System;
using System.Net.Http;
using System.Threading.Tasks;
using System.Windows;
using System.IO;
using System.Diagnostics;
using System.Security.Cryptography;
using Newtonsoft.Json;
using MaterialDesignThemes.Wpf;

namespace MinecraftLoader
{
    public partial class MainWindow : Window
    {
        private readonly HttpClient _httpClient;
        private readonly string _apiUrl = "http://localhost:8000/api/v1"; // Измените на ваш URL
        private string _currentKey;
        private string _downloadedFilePath;

        public MainWindow()
        {
            InitializeComponent();
            _httpClient = new HttpClient();
            LoadSettings();
        }

        private void LoadSettings()
        {
            try
            {
                if (File.Exists("settings.json"))
                {
                    var settings = JsonConvert.DeserializeObject<Settings>(File.ReadAllText("settings.json"));
                    _currentKey = settings.Key;
                    if (!string.IsNullOrEmpty(_currentKey))
                    {
                        KeyTextBox.Text = _currentKey;
                        ValidateKey();
                    }
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Ошибка при загрузке настроек: {ex.Message}", "Ошибка", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private void SaveSettings()
        {
            try
            {
                var settings = new Settings { Key = _currentKey };
                File.WriteAllText("settings.json", JsonConvert.SerializeObject(settings));
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Ошибка при сохранении настроек: {ex.Message}", "Ошибка", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private async void ValidateKey()
        {
            try
            {
                var response = await _httpClient.GetAsync($"{_apiUrl}/keys/validate?key={_currentKey}");
                if (response.IsSuccessStatusCode)
                {
                    var result = await response.Content.ReadAsStringAsync();
                    var keyInfo = JsonConvert.DeserializeObject<KeyInfo>(result);
                    
                    if (keyInfo.IsValid)
                    {
                        StatusText.Text = $"Ключ действителен. Осталось: {keyInfo.TimeRemaining}";
                        LaunchButton.IsEnabled = true;
                        SaveSettings();
                    }
                    else
                    {
                        StatusText.Text = "Ключ недействителен или истек";
                        LaunchButton.IsEnabled = false;
                    }
                }
                else
                {
                    StatusText.Text = "Ошибка при проверке ключа";
                    LaunchButton.IsEnabled = false;
                }
            }
            catch (Exception ex)
            {
                StatusText.Text = $"Ошибка: {ex.Message}";
                LaunchButton.IsEnabled = false;
            }
        }

        private async void LaunchButton_Click(object sender, RoutedEventArgs e)
        {
            try
            {
                LaunchButton.IsEnabled = false;
                StatusText.Text = "Загрузка файлов...";

                // Загрузка файла с сервера
                var response = await _httpClient.GetAsync($"{_apiUrl}/files/download");
                if (response.IsSuccessStatusCode)
                {
                    var tempPath = Path.Combine(Path.GetTempPath(), "minecraft_loader_temp");
                    Directory.CreateDirectory(tempPath);
                    _downloadedFilePath = Path.Combine(tempPath, "loader.zip");

                    using (var fileStream = File.Create(_downloadedFilePath))
                    {
                        await response.Content.CopyToAsync(fileStream);
                    }

                    // Запуск Minecraft
                    var minecraftPath = Path.Combine(
                        Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
                        ".minecraft"
                    );

                    var process = new Process
                    {
                        StartInfo = new ProcessStartInfo
                        {
                            FileName = "java",
                            Arguments = $"-jar {Path.Combine(minecraftPath, "versions", "1.8.9", "1.8.9.jar")}",
                            UseShellExecute = false,
                            RedirectStandardOutput = true,
                            CreateNoWindow = true
                        }
                    };

                    process.Start();
                    process.WaitForExit();

                    // Удаление временных файлов
                    if (File.Exists(_downloadedFilePath))
                    {
                        File.Delete(_downloadedFilePath);
                    }
                    if (Directory.Exists(tempPath))
                    {
                        Directory.Delete(tempPath, true);
                    }
                }
                else
                {
                    StatusText.Text = "Ошибка при загрузке файлов";
                }
            }
            catch (Exception ex)
            {
                StatusText.Text = $"Ошибка: {ex.Message}";
            }
            finally
            {
                LaunchButton.IsEnabled = true;
            }
        }

        private void KeyTextBox_TextChanged(object sender, System.Windows.Controls.TextChangedEventArgs e)
        {
            _currentKey = KeyTextBox.Text;
            if (!string.IsNullOrEmpty(_currentKey))
            {
                ValidateKey();
            }
            else
            {
                StatusText.Text = "Введите ключ";
                LaunchButton.IsEnabled = false;
            }
        }

        protected override void OnClosed(EventArgs e)
        {
            base.OnClosed(e);
            
            // Удаление временных файлов при закрытии
            try
            {
                if (!string.IsNullOrEmpty(_downloadedFilePath) && File.Exists(_downloadedFilePath))
                {
                    File.Delete(_downloadedFilePath);
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Ошибка при удалении временных файлов: {ex.Message}", "Ошибка", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }
    }

    public class Settings
    {
        public string Key { get; set; }
    }

    public class KeyInfo
    {
        public bool IsValid { get; set; }
        public string TimeRemaining { get; set; }
    }
} 