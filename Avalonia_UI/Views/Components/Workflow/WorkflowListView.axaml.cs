using Avalonia.Controls;
using Avalonia.Interactivity;
using Avalonia_UI.ViewModels;

namespace Avalonia_UI.Views.Components.Workflow;

public partial class WorkflowListView : UserControl
{
    public WorkflowListView()
    {
        InitializeComponent();
    }

    private async void ConfirmDeleteWorkflow(object? sender, RoutedEventArgs e)
    {
        if (DataContext is not MainWindowViewModel viewModel ||
            !viewModel.DeleteSelectedWorkflowCommand.CanExecute(null))
        {
            return;
        }

        try
        {
            await viewModel.DeleteSelectedWorkflowCommand.ExecuteAsync(null);
        }
        finally
        {
            DeleteWorkflowButton.Flyout?.Hide();
        }
    }
}
