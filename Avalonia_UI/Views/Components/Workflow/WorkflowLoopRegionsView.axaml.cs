using Avalonia.Controls;
using Avalonia.Interactivity;
using Avalonia_UI.ViewModels;

namespace Avalonia_UI.Views.Components.Workflow;

public partial class WorkflowLoopRegionsView : UserControl
{
    public WorkflowLoopRegionsView()
    {
        InitializeComponent();
    }

    private async void ConfirmDeleteLoopRegion(object? sender, RoutedEventArgs e)
    {
        if (DataContext is not WorkflowLoopRegionsViewModel viewModel ||
            !viewModel.DeleteSelectedRegionCommand.CanExecute(null))
        {
            return;
        }

        try
        {
            await viewModel.DeleteSelectedRegionCommand.ExecuteAsync(null);
        }
        finally
        {
            DeleteLoopRegionButton.Flyout?.Hide();
        }
    }
}
