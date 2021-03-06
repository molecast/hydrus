import ClientGUICommon
import HydrusGlobals as HG
import HydrusPaths
import json
import os
import wx

def DoFileExportDragDrop( window, page_key, media, cmd_down ):
    
    drop_source = wx.DropSource( window )
    
    data_object = wx.DataObjectComposite()
    
    #
    
    hydrus_media_data_object = wx.CustomDataObject( 'application/hydrus-media' )
    
    hashes = [ m.GetHash() for m in media ]
    
    if page_key is None:
        
        encoded_page_key = None
        
    else:
        
        encoded_page_key = page_key.encode( 'hex' )
        
    
    data = ( encoded_page_key, [ hash.encode( 'hex' ) for hash in hashes ] )
    
    data = json.dumps( data )
    
    hydrus_media_data_object.SetData( data )
    
    data_object.Add( hydrus_media_data_object, True )
    
    #
    
    file_data_object = wx.FileDataObject()
    
    client_files_manager = HG.client_controller.client_files_manager
    
    original_paths = []
    
    for m in media:
        
        hash = m.GetHash()
        mime = m.GetMime()
        
        original_path = client_files_manager.GetFilePath( hash, mime, check_file_exists = False )
        
        original_paths.append( original_path )
        
    
    #
    
    do_temp_dnd = False
    
    new_options = HG.client_controller.new_options
    
    if new_options.GetBoolean( 'discord_dnd_fix' ):
        
        if len( original_paths ) <= 10 and sum( ( os.path.getsize( path ) for path in original_paths ) ) < 50 * 1048576:
            
            do_temp_dnd = True
            
        
    
    temp_dir = HG.client_controller.temp_dir
    
    if do_temp_dnd and os.path.exists( temp_dir ):
        
        dnd_paths = []
        
        for original_path in original_paths:
            
            filename = os.path.basename( original_path )
            
            dnd_path = os.path.join( temp_dir, filename )
            
            if not os.path.exists( dnd_path ):
                
                HydrusPaths.MirrorFile( original_path, dnd_path )
                
            
            dnd_paths.append( dnd_path )
            
        
        flags = wx.Drag_AllowMove
        
    else:
        
        dnd_paths = original_paths
        
        if cmd_down:
            
            # secret dangerous discord compat mode
            flags = wx.Drag_AllowMove
            
        else:
            
            flags = wx.Drag_CopyOnly
            
        
    
    for path in dnd_paths:
        
        file_data_object.AddFile( path )
        
    
    data_object.Add( file_data_object )
    
    #
    
    drop_source.SetData( data_object )
    
    result = drop_source.DoDragDrop( flags )
    
    return result
    
class FileDropTarget( wx.DropTarget ):
    
    def __init__( self, parent, filenames_callable = None, url_callable = None, media_callable = None, page_callable = None ):
        
        wx.DropTarget.__init__( self )
        
        self._parent = parent
        
        self._filenames_callable = filenames_callable
        self._url_callable = url_callable
        self._media_callable = media_callable
        self._page_callable = page_callable
        
        self._receiving_data_object = wx.DataObjectComposite()
        
        self._hydrus_media_data_object = wx.CustomDataObject( 'application/hydrus-media' )
        self._hydrus_page_tab_data_object = wx.CustomDataObject( 'application/hydrus-page-tab' )
        self._file_data_object = wx.FileDataObject()
        self._text_data_object = wx.TextDataObject()
        
        self._receiving_data_object.Add( self._hydrus_media_data_object, True )
        self._receiving_data_object.Add( self._hydrus_page_tab_data_object )
        self._receiving_data_object.Add( self._file_data_object )
        self._receiving_data_object.Add( self._text_data_object )
        
        self.SetDataObject( self._receiving_data_object )
        
    
    def OnData( self, x, y, result ):
        
        if self.GetData():
            
            received_format = self._receiving_data_object.GetReceivedFormat()
            
            received_format_type = received_format.GetType()
            
            if received_format_type == wx.DF_FILENAME and self._filenames_callable is not None:
                
                paths = self._file_data_object.GetFilenames()
                
                wx.CallAfter( self._filenames_callable, paths ) # callafter to terminate dnd event now
                
                result = wx.DragNone
                
            elif received_format_type in ( wx.DF_TEXT, wx.DF_UNICODETEXT ) and self._url_callable is not None:
                
                text = self._text_data_object.GetText()
                
                wx.CallAfter( self._url_callable, text ) # callafter to terminate dnd event now
                
                result = wx.DragCopy
                
            else:
                
                try:
                    
                    format_id = received_format.GetId()
                    
                except:
                    
                    format_id = None
                    
                
                if format_id == 'application/hydrus-media' and self._media_callable is not None:
                    
                    mview = self._hydrus_media_data_object.GetData()
                    
                    data = mview.tobytes()
                    
                    ( encoded_page_key, encoded_hashes ) = json.loads( data )
                    
                    if encoded_page_key is not None:
                        
                        page_key = encoded_page_key.decode( 'hex' )
                        hashes = [ encoded_hash.decode( 'hex' ) for encoded_hash in encoded_hashes ]
                        
                        wx.CallAfter( self._media_callable, page_key, hashes ) # callafter so we can terminate dnd event now
                        
                    
                    result = wx.DragMove
                    
                
                if format_id == 'application/hydrus-page-tab' and self._page_callable is not None:
                    
                    mview = self._hydrus_page_tab_data_object.GetData()
                    
                    page_key = mview.tobytes()
                    
                    wx.CallAfter( self._page_callable, page_key ) # callafter so we can terminate dnd event now
                    
                    result = wx.DragMove
                    
                
            
        
        return result
        
    
    def OnDrop( self, x, y ):
        
        screen_position = ClientGUICommon.ClientToScreen( self._parent, ( x, y ) )
        
        drop_tlp = ClientGUICommon.GetXYTopTLP( screen_position )
        my_tlp = ClientGUICommon.GetTLP( self._parent )
        
        if drop_tlp == my_tlp:
            
            return True
            
        else:
            
            return False
            
        
    
    # setting OnDragOver to return copy gives Linux trouble with page tab drops with shift held down
