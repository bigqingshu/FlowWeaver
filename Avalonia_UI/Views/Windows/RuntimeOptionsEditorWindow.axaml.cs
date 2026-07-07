using Avalonia.Controls;
using Avalonia.Interactivity;

namespace Avalonia_UI.Views.Windows;

public partial class RuntimeOptionsEditorWindow : Window
{
    public RuntimeOptionsEditorWindow()
    {
        InitializeComponent();
    }

    private void CloseWindow(object? sender, RoutedEventArgs e)
    {
        Close();
    }
}
