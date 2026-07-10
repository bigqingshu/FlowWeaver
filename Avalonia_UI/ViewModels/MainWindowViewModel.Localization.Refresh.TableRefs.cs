namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void NotifyTableRefsLocalizedTextChanged()
    {
        OnPropertyChanged(nameof(TableRefsSectionText));
        OnPropertyChanged(nameof(DataPreviewSourceTableMetadataText));
        foreach (var tableRef in TableRefs)
        {
            tableRef.RefreshLocalizedText();
        }

        foreach (var state in DataPreviewStates)
        {
            state.RefreshLocalizedText();
        }
    }
}
