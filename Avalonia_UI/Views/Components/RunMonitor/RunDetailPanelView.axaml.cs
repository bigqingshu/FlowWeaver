using Avalonia.Controls;
using Avalonia.Interactivity;
using Avalonia_UI.ViewModels;
using Avalonia_UI.Views.Windows;

namespace Avalonia_UI.Views.Components.RunMonitor;

public partial class RunDetailPanelView : UserControl
{
    public RunDetailPanelView()
    {
        InitializeComponent();
    }

    private void OpenRunRuntimeOptionsWindow(object? sender, RoutedEventArgs e)
    {
        if (DataContext is not MainWindowViewModel mainViewModel
            || mainViewModel.CreateSelectedRunRuntimeOptionsViewModel() is not { } viewModel)
        {
            return;
        }

        var window = new WorkflowRunRuntimeOptionsWindow
        {
            DataContext = viewModel,
        };
        if (TopLevel.GetTopLevel(this) is Window owner)
        {
            window.Show(owner);
            return;
        }

        window.Show();
    }
}
