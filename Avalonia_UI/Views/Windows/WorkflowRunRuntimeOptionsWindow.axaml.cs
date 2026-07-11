using System;
using Avalonia.Controls;
using Avalonia.Interactivity;
using Avalonia_UI.ViewModels;

namespace Avalonia_UI.Views.Windows;

public partial class WorkflowRunRuntimeOptionsWindow : Window
{
    public WorkflowRunRuntimeOptionsWindow()
    {
        InitializeComponent();
        Opened += LoadRuntimeOptions;
    }

    private async void LoadRuntimeOptions(object? sender, EventArgs e)
    {
        Opened -= LoadRuntimeOptions;
        if (DataContext is WorkflowRunRuntimeOptionsViewModel viewModel)
        {
            await viewModel.LoadAsync();
        }
    }

    private void CloseWindow(object? sender, RoutedEventArgs e)
    {
        Close();
    }
}
