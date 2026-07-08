using System;
using System.Collections.ObjectModel;
using System.Linq;
using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.ComponentModel;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private bool isSynchronizingShellSelection;

    [ObservableProperty]
    private ShellPageKey selectedShellPageKey = ShellPageKey.Workflows;

    [ObservableProperty]
    private int selectedShellPageIndex;

    public ObservableCollection<ShellNavigationItemViewModel> ShellNavigationItems { get; } =
        new();

    public ShellNavigationItemViewModel WorkflowsNavigationItem =>
        GetShellNavigationItem(ShellPageKey.Workflows);

    public ShellNavigationItemViewModel DataPreviewNavigationItem =>
        GetShellNavigationItem(ShellPageKey.DataPreview);

    public ShellNavigationItemViewModel RunsNavigationItem =>
        GetShellNavigationItem(ShellPageKey.Runs);

    public ShellNavigationItemViewModel DataNavigationItem =>
        GetShellNavigationItem(ShellPageKey.Data);

    public ShellNavigationItemViewModel LogsNavigationItem =>
        GetShellNavigationItem(ShellPageKey.Logs);

    public ShellNavigationItemViewModel SettingsNavigationItem =>
        GetShellNavigationItem(ShellPageKey.Settings);

    public ShellNavigationItemViewModel SelectedShellNavigationItem =>
        GetShellNavigationItem(SelectedShellPageKey);

    public ShellPageContentKey SelectedShellPageContentKey =>
        SelectedShellNavigationItem.ContentKey;

    private void RefreshShellNavigationItems()
    {
        ShellNavigationItems.Clear();
        foreach (var descriptor in BuiltinShellPages.All.OrderBy(page => page.SortOrder))
        {
            ShellNavigationItems.Add(
                new ShellNavigationItemViewModel(
                    descriptor,
                    ResolveShellPageHeaderText(descriptor)));
        }

        SynchronizeSelectedShellPageIndex(SelectedShellPageKey);
        NotifyShellNavigationItemsChanged();
    }

    private ShellNavigationItemViewModel GetShellNavigationItem(ShellPageKey key)
    {
        return ShellNavigationItems.FirstOrDefault(item => item.Key == key)
            ?? throw new InvalidOperationException($"Shell navigation item '{key}' was not found.");
    }

    private int GetShellNavigationItemIndex(ShellPageKey key)
    {
        for (var index = 0; index < ShellNavigationItems.Count; index++)
        {
            if (ShellNavigationItems[index].Key == key)
            {
                return index;
            }
        }

        throw new InvalidOperationException($"Shell navigation item '{key}' was not found.");
    }

    private void NotifyShellNavigationItemsChanged()
    {
        OnPropertyChanged(nameof(ShellNavigationItems));
        OnPropertyChanged(nameof(WorkflowsNavigationItem));
        OnPropertyChanged(nameof(DataPreviewNavigationItem));
        OnPropertyChanged(nameof(RunsNavigationItem));
        OnPropertyChanged(nameof(DataNavigationItem));
        OnPropertyChanged(nameof(LogsNavigationItem));
        OnPropertyChanged(nameof(SettingsNavigationItem));
        OnPropertyChanged(nameof(SelectedShellNavigationItem));
        OnPropertyChanged(nameof(SelectedShellPageContentKey));
        OnPropertyChanged(nameof(SelectedShellPageIndex));
    }

    private string ResolveShellPageHeaderText(ShellPageDescriptor descriptor)
    {
        return descriptor.HeaderPropertyName switch
        {
            nameof(WorkflowsSectionText) => WorkflowsSectionText,
            nameof(DataPreviewTabText) => DataPreviewTabText,
            nameof(RunsSectionText) => RunsSectionText,
            nameof(DataTabText) => DataTabText,
            nameof(LogsTabText) => LogsTabText,
            nameof(SettingsMenuText) => SettingsMenuText,
            _ => throw new InvalidOperationException(
                $"Unknown shell page header property '{descriptor.HeaderPropertyName}'."),
        };
    }

}
