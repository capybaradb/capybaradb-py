from typing import Optional, List, Dict, Any
from ._emb_models import EmbModels
from ._vision_models import VisionModels
import base64


class EmbImage:
    """
    EmbImage - A specialized data type for storing and processing images in CapybaraDB
    
    EmbImage enables multimodal capabilities by storing images that can be:
    1. Processed by vision models to extract textual descriptions
    2. Embedded for vector search (using the extracted descriptions)
    3. Stored alongside other document data
    
    When stored in the database, the image is processed asynchronously in the background:
    - If a vision model is specified, the image is analyzed to generate textual descriptions
    - If an embedding model is specified, these descriptions are embedded for semantic search
    - The results are stored in the 'chunks' property
    
    Usage:
        ```python
        from capybaradb import CapybaraDB, EmbImage, VisionModels
        import base64
        
        # Read an image file and convert to base64
        with open("path/to/image.jpg", "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")
        
        # Create a document with an EmbImage field
        document = {
            "title": "Image Document",
            "image": EmbImage(
                image_data,
                mime_type="image/jpeg",  # Required: specify the image format
                # By default, uses VisionModels.GPT_4O_MINI and EmbModels.TEXT_EMBEDDING_3_SMALL
                # You can override with custom models:
                # vision_model=VisionModels.GPT_4O,
                # emb_model=EmbModels.TEXT_EMBEDDING_3_LARGE
            )
        }
        
        # Insert into CapybaraDB
        client = CapybaraDB()
        client.my_database.my_collection.insert([document])
        
        # Later, you can perform semantic searches that include image content
        ```
    """
    
    # List of supported embedding models for processing text chunks
    SUPPORTED_EMB_MODELS = [
        EmbModels.TEXT_EMBEDDING_3_SMALL,
        EmbModels.TEXT_EMBEDDING_3_LARGE,
        EmbModels.TEXT_EMBEDDING_ADA_002,
    ]
    
    # List of supported vision models for analyzing images
    SUPPORTED_VISION_MODELS = [
        VisionModels.GPT_4O_MINI,
        VisionModels.GPT_4O,
        VisionModels.GPT_4O_TURBO,
        VisionModels.GPT_O1,
    ]
    
    # List of supported mime types for images
    SUPPORTED_MIME_TYPES = [
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/gif",
        "image/webp",
    ]

    def __init__(
        self,
        data: str,  # base64 encoded image (change this if needed)
        mime_type: str,  # mime type of the image (required)
        emb_model: Optional[str] = EmbModels.TEXT_EMBEDDING_3_SMALL,
        vision_model: Optional[str] = VisionModels.GPT_4O_MINI,
        max_chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        is_separator_regex: Optional[bool] = None,
        separators: Optional[List[str]] = None,
        keep_separator: Optional[bool] = None,
    ):
        """
        Initialize an EmbImage object for image storage and processing.
        
        Args:
            data: Base64-encoded image data. Must be a non-empty string.
            
            mime_type: MIME type of the image (e.g., "image/jpeg", "image/png").
                      Must be one of the supported types. This parameter is required.
                      
            emb_model: The embedding model to use for text chunks. 
                      Defaults to EmbModels.TEXT_EMBEDDING_3_SMALL.
                      
            vision_model: The vision model to use for analyzing the image.
                         Defaults to VisionModels.GPT_4O_MINI.
                         
            max_chunk_size: Maximum character length for each text chunk.
                           Used when processing vision model output.
                           
            chunk_overlap: Number of overlapping characters between consecutive chunks.
                          
            is_separator_regex: Whether to treat separators as regex patterns.
            
            separators: List of separator strings or regex patterns.
            
            keep_separator: If True, separators remain in the chunked text.
        
        Raises:
            ValueError: If the data is not a valid string, if the mime_type is not supported,
                       or if the models are not supported.
        """
        if not self.is_valid_data(data):
            raise ValueError("Invalid data: must be a non-empty string containing valid base64-encoded image data.")
            
        if not self.is_valid_mime_type(mime_type):
            supported_list = ", ".join(self.SUPPORTED_MIME_TYPES)
            raise ValueError(f"Unsupported mime type: '{mime_type}'. Supported types are: {supported_list}")

        if emb_model is not None and not self.is_valid_emb_model(emb_model):
            supported_list = ", ".join(self.SUPPORTED_EMB_MODELS)
            raise ValueError(f"Invalid embedding model: '{emb_model}' is not supported. Supported models are: {supported_list}")

        if vision_model is not None and not self.is_valid_vision_model(vision_model):
            supported_list = ", ".join(self.SUPPORTED_VISION_MODELS)
            raise ValueError(f"Invalid vision model: '{vision_model}' is not supported. Supported models are: {supported_list}")

        self.data = data
        self.mime_type = mime_type
        self._chunks: List[str] = []  # Private attribute: updated only internally.
        self.emb_model = emb_model
        self.vision_model = vision_model
        self.max_chunk_size = max_chunk_size
        self.chunk_overlap = chunk_overlap
        self.is_separator_regex = is_separator_regex
        self.separators = separators
        self.keep_separator = keep_separator

    def __repr__(self):
        if self._chunks:
            return f'EmbImage("{self._chunks[0]}")'
        # Alternative representation when chunks are not set
        return "EmbImage(<raw data>)"

    @property
    def chunks(self) -> List[str]:
        """Read-only property for chunks."""
        return self._chunks

    @staticmethod
    def is_valid_data(data: str) -> bool:
        if not (isinstance(data, str) and data.strip() != ""):
            return False
        try:
            # Validate that data is a valid base64 encoded string.
            base64.b64decode(data, validate=True)
            return True
        except Exception:
            return False
            
    @classmethod
    def is_valid_mime_type(cls, mime_type: str) -> bool:
        """Check if the mime_type is supported."""
        return mime_type in cls.SUPPORTED_MIME_TYPES

    @classmethod
    def is_valid_emb_model(cls, emb_model: Optional[str]) -> bool:
        return emb_model is None or emb_model in cls.SUPPORTED_EMB_MODELS

    @classmethod
    def is_valid_vision_model(cls, vision_model: Optional[str]) -> bool:
        return vision_model is None or vision_model in cls.SUPPORTED_VISION_MODELS

    def to_json(self) -> Dict[str, Any]:
        """
        Convert the EmbImage instance to a JSON-serializable dictionary.
        Excludes all parameters with None values from the output.
        """
        # Start with required fields
        result = {
            "data": self.data,
            "mime_type": self.mime_type,
        }
        
        # Only include chunks if they exist
        if self._chunks:
            result["chunks"] = self._chunks
        
        # Add other fields only if they are not None
        if self.emb_model is not None:
            result["emb_model"] = self.emb_model
        if self.vision_model is not None:
            result["vision_model"] = self.vision_model
        if self.max_chunk_size is not None:
            result["max_chunk_size"] = self.max_chunk_size
        if self.chunk_overlap is not None:
            result["chunk_overlap"] = self.chunk_overlap
        if self.is_separator_regex is not None:
            result["is_separator_regex"] = self.is_separator_regex
        if self.separators is not None:
            result["separators"] = self.separators
        if self.keep_separator is not None:
            result["keep_separator"] = self.keep_separator
            
        return {"@embImage": result}

    @classmethod
    def from_json(cls, json_dict: Dict[str, Any]) -> "EmbImage":
        """
        Create an EmbImage instance from a JSON-serializable dictionary.
        Defaults are applied if any properties are missing.
        Assumes the input dictionary is the inner dictionary (i.e., the value under "@embImage").
        """
        image_data = json_dict.get("data")
        if image_data is None:
            raise ValueError("JSON data must include 'data' field under '@embImage'. This field should contain base64-encoded image data.")
            
        mime_type = json_dict.get("mime_type")
        if mime_type is None:
            supported_list = ", ".join(cls.SUPPORTED_MIME_TYPES)
            raise ValueError(f"JSON data must include 'mime_type' field under '@embImage'. Supported types are: {supported_list}")

        emb_model = json_dict.get("emb_model")
        vision_model = json_dict.get("vision_model")
        max_chunk_size = json_dict.get("max_chunk_size")
        chunk_overlap = json_dict.get("chunk_overlap")
        is_separator_regex = json_dict.get("is_separator_regex")
        separators = json_dict.get("separators")
        keep_separator = json_dict.get("keep_separator")

        instance = cls(
            image_data,
            mime_type,
            emb_model,
            vision_model,
            max_chunk_size,
            chunk_overlap,
            is_separator_regex,
            separators,
            keep_separator,
        )
        instance._chunks = json_dict.get("chunks", [])
        return instance
